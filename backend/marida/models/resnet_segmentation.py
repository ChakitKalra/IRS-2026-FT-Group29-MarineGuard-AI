"""Compact residual encoder-decoder for MARIDA pixel segmentation."""

import torch
from torch import nn
from torch.nn import functional as F


class ResidualBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, 3, stride=stride, padding=1, bias=False)
        self.norm1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False)
        self.norm2 = nn.BatchNorm2d(out_channels)
        self.skip = (
            nn.Identity()
            if in_channels == out_channels and stride == 1
            else nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels),
            )
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.skip(x)
        x = F.relu(self.norm1(self.conv1(x)), inplace=True)
        x = self.norm2(self.conv2(x))
        return F.relu(x + residual, inplace=True)


class ResNetSegmenter(nn.Module):
    """ResNet-style residual encoder with skip-connected segmentation head."""

    def __init__(
        self,
        in_channels: int = 11,
        num_classes: int = 12,
        width: int = 32,
        layers: tuple[int, int, int, int] = (2, 2, 2, 2),
        dropout: float = 0.0,
    ):
        super().__init__()
        if len(layers) != 4 or any(count < 1 for count in layers):
            raise ValueError("layers must contain four positive residual-block counts")
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, width, 3, padding=1, bias=False),
            nn.BatchNorm2d(width),
            nn.ReLU(inplace=True),
        )
        self.enc1 = self._make_layer(width, width, layers[0], stride=1)
        self.enc2 = self._make_layer(width, width * 2, layers[1], stride=2)
        self.enc3 = self._make_layer(width * 2, width * 4, layers[2], stride=2)
        self.enc4 = self._make_layer(width * 4, width * 8, layers[3], stride=2)
        self.dec3 = ResidualBlock(width * 12, width * 4)
        self.dec2 = ResidualBlock(width * 6, width * 2)
        self.dec1 = ResidualBlock(width * 3, width)
        self.dropout = nn.Dropout2d(dropout) if dropout > 0 else nn.Identity()
        self.classifier = nn.Conv2d(width, num_classes, kernel_size=1)

    @staticmethod
    def _make_layer(in_channels: int, out_channels: int, blocks: int, stride: int):
        layers = [ResidualBlock(in_channels, out_channels, stride=stride)]
        layers.extend(ResidualBlock(out_channels, out_channels) for _ in range(blocks - 1))
        return nn.Sequential(*layers)

    @staticmethod
    def _upsample_to(x: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
        return F.interpolate(x, size=reference.shape[-2:], mode="bilinear", align_corners=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(self.stem(x))
        e2 = self.enc2(e1)
        e3 = self.enc3(e2)
        e4 = self.enc4(e3)
        d3 = self.dec3(torch.cat((self._upsample_to(e4, e3), e3), dim=1))
        d2 = self.dec2(torch.cat((self._upsample_to(d3, e2), e2), dim=1))
        d1 = self.dec1(torch.cat((self._upsample_to(d2, e1), e1), dim=1))
        return self.classifier(self.dropout(d1))
