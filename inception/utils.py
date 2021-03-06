import torch

from inception import inception_v3


def load_model_with_placement(placement, lr=0.01, classes=1000):
    device_lookup = {
        0: 'cpu:0',
        1: 'cpu:0',
        2: 'cuda:0',
        3: 'cuda:1'
    }

    if placement is None:
        placement = 'cpu:0'
    elif isinstance(placement, dict):
        translated_placement = {}
        for layer_name, device in placement.items():
            translated_placement[layer_name] = device_lookup[device]
        placement = translated_placement

    model = inception_v3(pretrained=False, placement=placement, num_classes=classes, init_weights=False)

    if isinstance(placement, str):
        input_device = output_device = torch.device(placement)
        model.to(input_device)
    else:
        input_device = placement['Conv2d_1a_3x3']
        output_device = placement['softmax']

    criterion = torch.nn.CrossEntropyLoss().to(output_device)  # TODO Move loss to correct device
    optimizer = torch.optim.SGD(model.parameters(), lr=lr)

    return model, criterion, optimizer, input_device, output_device
