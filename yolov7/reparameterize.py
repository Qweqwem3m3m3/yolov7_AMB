# import
from copy import deepcopy
from models.yolo import Model
import torch
from utils.torch_utils import select_device, is_parallel
import yaml

weights = 'THE PATH YOU FIND/best.pt'
class_num = 1
custom_yaml = '/content/yolov7/cfg/deploy/yolov7-tiny.yaml'
target = '/content/yolov7/best_Reparameterize.pt'

device = select_device('0', batch_size=1)
# model trained by cfg/training/*.yaml
ckpt = torch.load(weights, map_location=device, weights_only=False)
# reparameterized model in cfg/deploy/*.yaml
model = Model(custom_yaml, ch=3, nc=class_num).to(device)

with open(custom_yaml) as f:
    yml = yaml.load(f, Loader=yaml.SafeLoader)
anchors = len(yml['anchors'][0]) // 2

# copy intersect weights
state_dict = ckpt['model'].float().state_dict()
exclude = []
intersect_state_dict = {k: v for k, v in state_dict.items() if k in model.state_dict() and not any(x in k for x in exclude) and v.shape == model.state_dict()[k].shape}
model.load_state_dict(intersect_state_dict, strict=False)
model.names = ckpt['model'].names
model.nc = ckpt['model'].nc

# reparametrized YOLOR
for i in range((model.nc+5)*anchors):
    model.state_dict()['model.77.m.0.weight'].data[i, :, :, :] *= state_dict['model.77.im.0.implicit'].data[:, i, : :].squeeze()
    model.state_dict()['model.77.m.1.weight'].data[i, :, :, :] *= state_dict['model.77.im.1.implicit'].data[:, i, : :].squeeze()
    model.state_dict()['model.77.m.2.weight'].data[i, :, :, :] *= state_dict['model.77.im.2.implicit'].data[:, i, : :].squeeze()
model.state_dict()['model.77.m.0.bias'].data += state_dict['model.77.m.0.weight'].mul(state_dict['model.77.ia.0.implicit']).sum(1).squeeze()
model.state_dict()['model.77.m.1.bias'].data += state_dict['model.77.m.1.weight'].mul(state_dict['model.77.ia.1.implicit']).sum(1).squeeze()
model.state_dict()['model.77.m.2.bias'].data += state_dict['model.77.m.2.weight'].mul(state_dict['model.77.ia.2.implicit']).sum(1).squeeze()
model.state_dict()['model.77.m.0.bias'].data *= state_dict['model.77.im.0.implicit'].data.squeeze()
model.state_dict()['model.77.m.1.bias'].data *= state_dict['model.77.im.1.implicit'].data.squeeze()
model.state_dict()['model.77.m.2.bias'].data *= state_dict['model.77.im.2.implicit'].data.squeeze()

# model to be saved
ckpt = {'model': deepcopy(model.module if is_parallel(model) else model).half(),
        'optimizer': None,
        'training_results': None,
        'epoch': -1}

# save reparameterized model
torch.save(ckpt, target)

