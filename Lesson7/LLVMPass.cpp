#include "llvm/Pass.h"
#include "llvm/IR/Module.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/Support/raw_ostream.h"
#include <string>

using namespace llvm;

namespace {

struct SkeletonPass : public PassInfoMixin<SkeletonPass> {
    PreservedAnalyses run(Module &M, ModuleAnalysisManager &AM) {
        std::string module_name(M.getName());
        if (module_name.find("diffuse.cpp") != std::string::npos) {
            int counter = 0;
            for (auto &F : M) {
                std::string function_name(F.getName());
                if (function_name.find("pdf") != std::string::npos && function_name.find("_pdf") == std::string::npos && counter==0) {
                    counter = 1;

                    for (auto &B : F) {
                        for (auto &I : B) {
                            if (auto *RetInst = dyn_cast<ReturnInst>(&I)) {
                                if (RetInst->getNumOperands() == 1) {
                                    Value* ret_val = RetInst->getOperand(0);
                                    IRBuilder<> Builder(RetInst);
                                    Value *div = Builder.CreateFMul(ret_val, ConstantFP::get(ret_val->getType(), 100.0f));
                                    RetInst->setOperand(0, div);
                                }

                            }
                        }
                    }
                }
            }
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
