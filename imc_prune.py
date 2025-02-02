
# Environment imports
import torch
import warnings
import torch_pruning as tp
from torch.nn import modules
from torchvision.models.resnet import BasicBlock
from torchvision.models.resnet import Bottleneck
from torchvision.models.quantization.resnet import QuantizableBasicBlock
from torchvision.models.quantization.resnet import QuantizableBottleneck
from torchvision.models.quantization.resnet import BasicBlock
from torchvision.models.quantization.resnet import Bottleneck

warnings.filterwarnings("ignore")
device = torch.device('cuda')


def prune_model(name='', model=None, dir_models='', suffix='_pruned', im_size=224):
    print('\nPruning Model: ' + name + '...', end='\t')

    model.to(device)

    strategy = tp.strategy.L1Strategy()
    DG = tp.DependencyGraph().build_dependency(model, example_inputs=torch.randn(1, 3, im_size, im_size))

    def prune_conv(conv, amount=0.2):
        pruning_index = strategy(conv.weight, amount=amount)
        plan = DG.get_pruning_plan(conv, tp.prune_conv, pruning_index)
        plan.exec()

    block_prune_probs = [0.1, 0.1, 0.2, 0.2, 0.2, 0.2, 0.3, 0.3]
    # block_prune_probs = [0.2, 0.2, 0.2, 0.2, 0.3, 0.3, 0.3, 0.3]
    limit = len(block_prune_probs) - 1
    blk_id = 0
    conv_index = 0
    prev_conv = False
    for m in list(model.modules())[1:]:
        if isinstance(m, modules.Conv2d):
            prev_conv = True
            conv_index += 1
        if isinstance(m, modules.Linear) and prev_conv:
            break

    for m in list(model.modules()):
        if isinstance(m, modules.Conv2d) and 'resnet' not in name.lower():
            if 'naber' not in name.lower() or ('naber' in name.lower() and conv_index > 1):
                prune_conv(m)
                conv_index -= 1
        if isinstance(m, BasicBlock) or isinstance(m, Bottleneck):
            prune_conv(m.conv1, block_prune_probs[blk_id])
            prune_conv(m.conv2, block_prune_probs[blk_id])
            if blk_id < limit - 1:
                blk_id += 1

    print('COMPLETE')

    # 5. Save Model
    print('Saving', name + suffix + '...', end='\t')
    filename = dir_models + name + suffix + ".pth"
    torch.save(model, filename)
    print('COMPLETE')
    return torch.load(filename)


def quantize_model(name='', model=None, dir_models='', suffix='_quant'):
    print('\nQuantizing Model: ' + name + '...', end='\t')

    model.to(torch.device('cpu'))
    model = torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
    print('COMPLETE')

    # 5. Save Model
    print('Saving', name + suffix + '...', end='\t')
    filename = dir_models + name + suffix + ".pth"
    torch.save(model, filename)
    print('COMPLETE')

    return model
