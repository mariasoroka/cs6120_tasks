#include "llvm/Pass.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Module.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Analysis/LoopInfo.h"
#include "llvm/Analysis/LoopPass.h"
#include "llvm/IR/Dominators.h"
#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/PassManager.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"
#include "llvm/Transforms/Utils/LoopSimplify.h"
#include "llvm/ADT/DenseMap.h"
#include <vector>

using namespace llvm;

namespace {

struct SkeletonPass : public PassInfoMixin<SkeletonPass> {
    PreservedAnalyses run(Module &M, ModuleAnalysisManager &MAM) {
        // errs() << "Module name: " << M.getName() << "\n";
        std::string module_name(M.getName());

        if (module_name.find("/Benchmarks/src/") != std::string::npos) {
            auto &FAM = MAM.getResult<FunctionAnalysisManagerModuleProxy>(M).getManager();
            for (auto &F : M) {
                if (!F.isDeclaration()) {
                    // errs() << "Function name: " << F.getName() << "\n";
                    auto &Loops = FAM.getResult<LoopAnalysis>(F);
                    auto &DT = FAM.getResult<DominatorTreeAnalysis>(F);
                    for (auto &Loop : Loops) {

                        if (simplifyLoop(Loop, &DT, &Loops, nullptr, nullptr, nullptr, true)) {
                            DenseMap<Instruction *, bool> LoopInvariantSet;
                            DenseSet<Value *> CanBeAltered;
                            for (auto *Block : Loop->getBlocks()) {
                                for (auto &Inst : *Block) {
                                    // errs() << "Instruction: " << Inst << "\n";
                                    LoopInvariantSet[&Inst] = false;
                                    if (Inst.mayHaveSideEffects() || !Inst.isSafeToRemove()) {
                                        for (auto &Op : Inst.operands()) {
                                            if (auto *OpInst = dyn_cast<Instruction>(Op)) {
                                                CanBeAltered.insert(OpInst);
                                            }
                                        }
                                        CanBeAltered.insert(&Inst);
                                    }
                                }
                            }

                            int num_invariant = 0;
                            int num_new_invariant = 0;
                            do {
                                num_invariant = num_new_invariant;
                                num_new_invariant = 0;
                                for (auto *Block : Loop->getBlocks()) {
                                    for (auto &Inst : *Block) {
                                        if (LoopInvariantSet[&Inst]) {
                                            num_new_invariant++;
                                        }
                                        else if (Inst.isSafeToRemove() && !Inst.mayHaveSideEffects() && !isa<PHINode>(&Inst) && 
                                                    !(isa<GetElementPtrInst>(&Inst) && (dyn_cast<GetElementPtrInst>(&Inst))->isInBounds()) &&
                                                    !(isa<BinaryOperator>(&Inst) && (dyn_cast<BinaryOperator>(&Inst)->hasNoUnsignedWrap())) &&
                                                    !(isa<BinaryOperator>(&Inst) && (dyn_cast<BinaryOperator>(&Inst)->hasNoSignedWrap()))){
                                            bool is_loop_invariant = true;
                                            for (auto &Op : Inst.operands()) {
                                                if (auto *OpInst = dyn_cast<Instruction>(Op)) {
                                                    if (CanBeAltered.count(OpInst)) {
                                                        is_loop_invariant = false;
                                                    }
                                                    if (LoopInvariantSet.contains(OpInst) && !LoopInvariantSet[OpInst]) {
                                                        is_loop_invariant = false;
                                                    }
                                                    
                    
                                                }
                                                if (isa<GlobalVariable>(Op)) {
                                                    is_loop_invariant = false;
                                                }
                                            }
                                            if (is_loop_invariant) {
                                                LoopInvariantSet[&Inst] = true;
                                                num_new_invariant++;
                                            }
                                        }
                                    }
                                }
                            } while (num_invariant != num_new_invariant);

                            std::vector<Instruction *> RemovableLoopInvariantInstructions;
                            for (auto *Block : Loop->getBlocks()) {
                                for (auto &Inst : *Block) {
                                    if (Inst.isSafeToRemove() && !Inst.mayHaveSideEffects() && LoopInvariantSet[&Inst]) {
                                        bool is_used_outside_loop = false;
                                        for (auto &Use : Inst.uses()) {
                                            User* user = Use.getUser();
                                            if (Instruction *userInst = dyn_cast<Instruction>(user)) {
                                                if (!Loop->contains(userInst)) {
                                                    is_used_outside_loop = true;
                                                    break;
                                                }
                                            }
                                        }
                                        if (!is_used_outside_loop) {
                                            RemovableLoopInvariantInstructions.push_back(&Inst);
                                        }
                                    }
                                }
                            }


                            auto preheader = Loop->getLoopPreheader();
                            // for (auto *Inst : RemovableLoopInvariantInstructions) {
                            //     errs() << "Instruction: " << *Inst << " moved to preheader\n";
                            // }

                            for (auto *Inst : RemovableLoopInvariantInstructions) {
                                Instruction *NewInst = Inst->clone();
                                NewInst->insertBefore(preheader->getTerminator()); 
                                Inst->replaceAllUsesWith(NewInst);
                            }
                            for (auto *Inst : RemovableLoopInvariantInstructions) {
                                Inst->eraseFromParent();
                            }
                        


                        }
                    }
                }
            }

            // errs() << "Done\n";
        }
        return PreservedAnalyses::none();
    };
};

}

extern "C" LLVM_ATTRIBUTE_WEAK ::llvm::PassPluginLibraryInfo
llvmGetPassPluginInfo() {
    return {
        .APIVersion = LLVM_PLUGIN_API_VERSION,
        .PluginName = "Skeleton pass",
        .PluginVersion = "v0.1",
        .RegisterPassBuilderCallbacks = [](PassBuilder &PB) {
            PB.registerPipelineStartEPCallback(
                [](ModulePassManager &MPM, OptimizationLevel Level) {
                    MPM.addPass(SkeletonPass());
                });
        }
    };
}
