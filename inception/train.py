import sys
import json
import os
import time
import argparse

from utils import load_model_with_placement
import torchvision
from torchvision import transforms
import torch.utils.data


def train_single_batch(model, data, criterion, optimizer):
    output, aux_output = model(data[0])
    loss1 = criterion(output, data[1])
    loss2 = criterion(aux_output, data[1])
    loss = loss1 + 0.4 * loss2
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    return loss


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train Inception_v3')
    parser.add_argument('--epochs', dest='epochs', default=10, type=int, help='Number of epochs to train the network for.')
    parser.add_argument('--dataset', dest='dataset', default='mnist',
                        help='The dataset that the network should be trained on. [mnist, cats_vs_dogs]')
    parser.add_argument('--lr', dest='lr', default=0.01, help='Learning rate of the optimizer')
    parser.add_argument('--batch_size', dest='batch_size', default=128, help='Batch size for the learning process')
    parser.add_argument('--placement', '-p', dest='placement', default='cuda:0',
                        help='Placement specification for the network; either a single device '
                             'or path to an assignment file.')

    args = parser.parse_args()

    EPOCHS = args.epochs
    DATASET = args.dataset
    LEARNING_RATE = args.lr
    BATCH_SIZE = args.batch_size

    if os.path.exists(args.placement):
        with open(args.placement) as f:
            placement = json.load(f)
    else:
        placement = args.placement

    dataset_classes = {
        'mnist': 10,
        'cats_vs_dogs': 2
    }

    model, criterion, optimizer, input_device, output_device = load_model_with_placement(placement, lr=LEARNING_RATE,
                                                                                         classes=dataset_classes[DATASET])

    if DATASET == 'mnist':
        preprocess = transforms.Compose([
            transforms.Grayscale(3),
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])

        train_dataset = torchvision.datasets.MNIST('../mnist_data', train=True, download=True, transform=preprocess)
        test_dataset = torchvision.datasets.MNIST('../mnist_data', train=False, download=True, transform=preprocess)

    elif DATASET == 'cats_vs_dogs':
        preprocess = transforms.Compose([
            transforms.Resize(299),
            transforms.CenterCrop(299),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        train_dataset = torchvision.datasets.ImageFolder('../cvd_data/train', transform=preprocess)
        test_dataset = torchvision.datasets.ImageFolder('../cvd_data/test', transform=preprocess)

    else:
        sys.exit(1)

    test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=2)
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=2)

    model.train()

    average_batch_times = []

    for epoch in range(EPOCHS):
        running_loss = 0.0
        running_time = 0.0
        batches = 0
        for i, batch in enumerate(train_loader):
            batches += 1
            torch.cuda.synchronize()
            batch = batch[0].to(input_device), batch[1].to(output_device)
            start = time.time()
            loss = train_single_batch(model, batch, criterion, optimizer)
            torch.cuda.synchronize()
            end = time.time()
            running_time += (end - start) * 1000
            running_loss += loss.item()

            if i % 50 == 49:
                print(f'[Epoch {epoch + 1}, Batch {i + 1}] Loss: {running_loss / 50}')
                running_loss = 0

        average_batch_time = running_time / batches
        print(f'[Epoch {epoch + 1}] Average batch time: {average_batch_time:.3f}ms')
        average_batch_times.append(average_batch_time)

    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for data in test_loader:
            data = data[0].to(input_device), data[1].to(output_device)
            images, labels = data
            outputs = model(images)
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    print(f'Accuracy: {correct / total:.2%}')