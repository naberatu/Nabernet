import torch
import torch.nn as nn
import torch.nn.functional as F
from net import Net
import torchvision
import torchvision.transforms as transforms
import torch.optim as optim
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

# Parameters
# ============================================================================================
PATH = './cifar_net.pth'
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
# IMSIZE = 256
# LOADER = transforms.Compose([transforms.Scale(IMSIZE), transforms.ToTensor()])

# Loading CIFAR-10
# ============================================================================================
transform = transforms.Compose(
            [transforms.ToTensor(),
             transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])

trainset = torchvision.datasets.CIFAR10(root='./data', train=True,
                                                download=False, transform=transform)
trainloader = torch.utils.data.DataLoader(trainset, batch_size=4,
                                                 shuffle=True, num_workers=2)

testset = torchvision.datasets.CIFAR10(root='./data', train=False,
                                               download=False, transform=transform)
testloader = torch.utils.data.DataLoader(testset, batch_size=4,
                                                 shuffle=False, num_workers=2)

classes = ('plane', 'car', 'bird', 'cat',
           'deer', 'dog', 'frog', 'horse', 'ship', 'truck')

# stlset = torchvision.datasets.STL10(root='./data', download=True)


def imshow(img):
    img = img / 2 + 0.5     # unnormalize
    npimg = img.numpy()
    plt.imshow(np.transpose(npimg, (1, 2, 0)))
    plt.show()


# def imload(img):
#     image = Image.open(img)
#     image = LOADER(image).float()
#     # image = (image, requires_grad=True)
#     image = image.unsqueeze(0)  # this is for VGG, may not be needed for ResNet
#     return image.cuda()  # assumes that you're using GPU

# IMAGE = imload('C:\\Users\\elite\\Desktop\\cat.png')

if __name__ == '__main__':

    net = Net()    # Summon Neural Net

    # Data Iterator
    # ================================================================
    dataiter = iter(trainloader)
    # dataiter = iter(testloader)
    images, labels = dataiter.next()
    print('| Truth:\t\t ', ' '.join('%5s' % classes[labels[j]] for j in range(4)))
    # imshow(torchvision.utils.make_grid(images))   # Displays images

    # # Training algorithm
    # # ======================================================================
    # net.to(DEVICE)  # Only for training
    # criterion = nn.CrossEntropyLoss()
    # optimizer = optim.SGD(net.parameters(), lr=0.001, momentum=0.9)
    #
    # for epoch in range(12):  # loop over the dataset multiple times
    #     running_loss = 0.0
    #     for i, data in enumerate(trainloader, 0):
    #         # get the inputs; data is a list of [inputs, labels]
    #         inputs, labels = data[0].to(DEVICE), data[1].to(DEVICE)
    #
    #         # zero the parameter gradients
    #         optimizer.zero_grad()
    #
    #         # forward + backward + optimize
    #         outputs = net(inputs)
    #         loss = criterion(outputs, labels)
    #         loss.backward()
    #         optimizer.step()
    #
    #         # print statistics
    #         running_loss += loss.item()
    #         if i % 2000 == 1999:    # print every 2000 mini-batches
    #             print('[%d, %5d] loss: %.3f' %
    #                   (epoch + 1, i + 1, running_loss / 2000))
    #             running_loss = 0.0
    #
    # print('Finished Training')
    # torch.save(net.state_dict(), PATH)

    # Neural Net` Testing
    # ==========================================================
    net.load_state_dict(torch.load(PATH))
    outputs = net(images)
    # net(IMAGE)
    _, predicted = torch.max(outputs, 1)
    print('| Predicted:\t ', ' '.join('%5s' % classes[predicted[j]]
                                    for j in range(4)))

    # Test Run: Overall
    correct = 0
    total = 0
    with torch.no_grad():
        for data in testloader:
            images, labels = data
            outputs = net(images)
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    print('\n| Accuracy of the network on the 10000 test images: %d %%' % (
            100 * correct / total))

    # Test Run: Breakdown
    class_correct = list(0. for i in range(10))
    class_total = list(0. for i in range(10))
    with torch.no_grad():
        for data in testloader:
            images, labels = data
            outputs = net(images)
            _, predicted = torch.max(outputs, 1)
            c = (predicted == labels).squeeze()
            for i in range(4):
                label = labels[i]
                class_correct[label] += c[i].item()
                class_total[label] += 1

    for i in range(10):
        print('| Accuracy of %5s : %2d %%' % (
            classes[i], 100 * class_correct[i] / class_total[i]))
