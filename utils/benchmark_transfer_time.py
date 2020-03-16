import torch
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
sns.set()


def benchmark_bandwidth(tensor_size, source_device, target_device):
    source_device = torch.device(source_device)
    target_device = torch.device(target_device)
    t = torch.rand((tensor_size // 4,))
    t.to(source_device)
    torch.cuda.synchronize()

    start_time = time.time()
    t.to(target_device)
    torch.cuda.synchronize()
    end_time = time.time()
    transfer_time = end_time - start_time

    tensor_size = t.nelement() * t.element_size()
    bandwidth = tensor_size / transfer_time  # Bytes / second
    bandwidth = (bandwidth * 8) / 10**6  # Mbit/s

    return bandwidth


def plot_results_from_file(file_path, source_device, target_device, server_name):
    results = pd.read_csv(file_path, skiprows=1, names=['tensor_size', 'bandwidth'])

    sns.lineplot(x='tensor_size', y='bandwidth', data=results)
    plt.xscale('log')
    plt.xlabel('Tensor size (Bytes)')
    plt.ylabel('Bandwidth (Mbit/s)')
    plt.title(f'Transfer from {source_device} to {target_device} ({server_name})')

    plt.show()


def benchmark_multiple_tensor_sizes(tensor_sizes, source_device='cpu', target_device='cuda:0', transfer_repeats=10,
                                    result_file='./bandwidth.csv'):
    with open(result_file, 'w') as f:
        f.write('tensor_size, bandwidth')

    for tensor_size in tensor_sizes:
        print(f'Benchmarking tensor of size {tensor_size / 10**6:.3f}MB... ', end='')
        bandwidths = [benchmark_bandwidth(tensor_size, source_device, target_device) for i in range(transfer_repeats)]

        for bandwidth in bandwidths:
            with open(result_file, 'a') as f:
                f.write(f'{tensor_size}, {bandwidth}\n')

        print(f'{sum(bandwidths) / len(bandwidths)}Mbit/s')


if __name__ == '__main__':
    result_file = './bandwidth.csv'
    source_device = 'cpu'
    target_device = 'cuda:0'
    transfer_repeats = 10
    tensor_sizes = [10**i for i in range(3, 10)]

    benchmark_multiple_tensor_sizes(tensor_sizes, source_device, target_device, transfer_repeats, result_file)

