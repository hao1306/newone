import sys
sys.path.append('.')

import os
import argparse
import torch
from networks.resnet import resnet_model
from torch.utils.data import DataLoader
from data_preparation.resnet_data import SimulatorDataset
import utils
import cv2
from torch.autograd import Variable
import numpy as np


def train_val(cfg):
    if cfg.device == 'cpu':
        device = torch.device('cpu')
    else:
        os.environ['CUDA_VISIBLE_DEVICES'] = cfg.device
        device = torch.device('gpu:0')

    # 第1步：构建数据读取迭代器

    train_data = SimulatorDataset(data_path=cfg.train_data)
    val_data = SimulatorDataset(data_path=cfg.val_data)

    train_dataloader = DataLoader(train_data, batch_size=cfg.batch_size, shuffle=True, num_workers=cfg.num_workers, pin_memory=True)
    val_dataloader = DataLoader(val_data, batch_size=cfg.batch_size*2, shuffle=False, num_workers=cfg.num_workers, pin_memory=True)

    # 第2步：构建网络，设置训练参数：学习率、学习率衰减策略、优化函数（SDG、Adam、……）、损失函数、……

    model = resnet_model().to(device=device)

    optimizer = torch.optim.SGD(model.parameters(), lr=cfg.learning_rate)

    loss_function = torch.nn.MSELoss()

    # 第3步：循环读取数据训练网络
    
    for epoch_i in range(cfg.epochs):
        model.train()

        for train_i, (img_path, target) in enumerate(train_dataloader):
            steering = target[2]
            img = cv2.imread(img_path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = utils.preprocess(img)
            img, steering = utils.random_flip(img, steering)
            img, steering = utils.random_translate(img, steering, 100, 10)
            img = utils.random_shadow(img)
            img = utils.random_brightness(img)
            img = Variable(torch.cuda.FloatTensor([img]))
            target[2] = steering
            target = np.array([target]).astype(float)
            target = Variable(torch.cuda.FloatTensor(target))
            input = img.permute(0, 3, 1, 2)
            input, target = input.to(device), target.to(device)

            optimizer.zero_grad()

            output = model(input)
            loss = loss_function(output, target)

            print(loss.item())

            loss.backward()
            optimizer.step()

        # 训练完每个epoch进行验证
        model.eval()
        with torch.no_grad():
            loss_sum = 0
            for val_i, (img_path, target) in enumerate(val_dataloader):
                steering = target[2]
                img = cv2.imread(img_path)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = utils.preprocess(img)
                img, steering = utils.random_flip(img, steering)
                img, steering = utils.random_translate(img, steering, 100, 10)
                img = utils.random_shadow(img)
                img = utils.random_brightness(img)
                img = Variable(torch.cuda.FloatTensor([img]))
                target[2] = steering
                target = np.array([target]).astype(float)
                target = Variable(torch.cuda.FloatTensor(target))
                input = img.permute(0, 3, 1, 2)
                input, target = input.to(device), target.to(device)
                output = model(input)
                loss_sum = loss_sum + loss_function(output, target)
            print(val_i)
            print('val_loss:', loss_sum.item()/(val_i+1))

        torch.save(model, cfg.save_path+'/'+str(epoch_i)+'.pt')
        torch.cuda.empty_cache()

def parse_cfg():
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=100, help='total number of training epochs')
    parser.add_argument('--train-data', type=str, default='Dataset/VehicleData.txt', help='data path')
    parser.add_argument('--val-data', type=str, default='Dataset/VehicleData.txt', help='data path')
    parser.add_argument('--device', type=str, default='cpu', help='e.g. cpu or 0 or 0,1,2,3')
    parser.add_argument('--batch-size', type=int, default=2, help='batch size')
    parser.add_argument('--learning-rate', type=int, default=0.01, help='initial learning rate')
    parser.add_argument('--num-workers', type=int, default=0, help='number of workers')
    parser.add_argument('--save-path', type=str, default='weights/resnet', help='path to save checkpoint')

    return parser.parse_args()

if __name__ == '__main__':
    cfg = parse_cfg()
    
    train_val(cfg)

    