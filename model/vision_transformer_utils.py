# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
#

import math

import torch

from logging import getLogger

logger = getLogger()


def _no_grad_trunc_normal_(tensor, mean, std, a, b):
    # Cut & paste from PyTorch official master until it's in a few official releases - RW
    # Method based on https://people.sc.fsu.edu/~jburkardt/presentations/truncated_normal.pdf
    def norm_cdf(x):
        # Computes standard normal cumulative distribution function
        return (1. + math.erf(x / math.sqrt(2.))) / 2.

    with torch.no_grad():
        # Values are generated by using a truncated uniform distribution and
        # then using the inverse CDF for the normal distribution.
        # Get upper and lower cdf values
        l = norm_cdf((a - mean) / std)
        u = norm_cdf((b - mean) / std)

        # Uniformly fill tensor with values from [l, u], then translate to
        # [2l-1, 2u-1].
        tensor.uniform_(2 * l - 1, 2 * u - 1)

        # Use inverse cdf transform for normal distribution to get truncated
        # standard normal
        tensor.erfinv_()

        # Transform to proper mean, std
        tensor.mul_(std * math.sqrt(2.))
        tensor.add_(mean)

        # Clamp to ensure it's in the proper range
        tensor.clamp_(min=a, max=b)
        return tensor


def trunc_normal_(tensor, mean=0., std=1., a=-2., b=2.):
    # type: (Tensor, float, float, float, float) -> Tensor
    return _no_grad_trunc_normal_(tensor, mean, std, a, b)


def apply_masks(x, masks):
    """
    :param x: tensor of shape [B (batch-size), N (num-patches), D (feature-dim)]
    :param masks: list of tensors containing indices of patches in [N] to keep
    """
    all_x = []
    for m in masks:
        mask_keep = m.unsqueeze(-1).repeat(1, 1, x.size(-1))
        all_x += [torch.gather(x, dim=1, index=mask_keep)]
    return torch.cat(all_x, dim=0)


def repeat_interleave_batch(x, B, repeat):    ## [32, 200, 256], 32, 1
    N = len(x) // B
    # print("N: ", N, f"B: {B}, repeat: {repeat}")    
    x = torch.cat([
        torch.cat([x[i*B:(i+1)*B] for _ in range(repeat)], dim=0)
        for i in range(N)
    ], dim=0)
    return x


# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
#

import torch


def apply_masks(x, masks):
    """
    :param x: tensor of shape [B (batch-size), N (num-patches), D (feature-dim)]
    :param masks: list of tensors containing indices of patches in [N] to keep  
    """
    all_x = []
    for m in masks:
        mask_keep = m.unsqueeze(-1).repeat(1, 1, x.size(-1))
        all_x += [torch.gather(x, dim=1, index=mask_keep)]
    return torch.cat(all_x, dim=0)

def apply_masks_targets(x, masks):
    """
    :param x: tensor of shape [B (batch-size), N (num-patches), D (feature-dim)]
    :param masks: tensor of shape [B (batch-size), num_masks, num_patches]
    returns: tensor of shape [B*num_masks, num of target tokens per sample per mask, D]
    """
    all_x = []   ## maintain a list for storing all 
    masks = masks.transpose(0, 1)  ## [B, num_masks, N] -> [num_masks, B, N]
    for m in masks:
        ## m is [B, N]
        # print("in apply_masks_targets: \n", "m.shape: ", sum(m), " x.shape: ", x.shape) ##[32, 200], [32, 200, 256]
        # mask_keep = m.unsqueeze(-1).repeat(1, 1, x.size(-1))
        # print("mask_keep.shape: ", mask_keep.shape)    ## [32, 200, 256]
        x_ = [x[i][m[i].bool()] for i in range(x.shape[0])]
        
        x_ = torch.stack(x_, dim=0)
        # print("x_.shape: ", x_.shape)    ## [32, 12, 256]
        # print(f"len(x_): {len(x_)}", "x_[0].shape: ", x_[0].shape)    ## [num of target tokens per sample per mask, D]
        all_x += [x_]
    # print(f"len(all_x): {len(all_x)}")
    all_x = torch.cat(all_x, dim=0)
    # print("all_x.shape: ", all_x.shape)    ## [32*4, 12, 256]
    return all_x

def apply_masks_ctxt(x, masks):
    """
    :param x: tensor of shape [B (batch-size), N (num-patches), D (feature-dim)]
    :param masks: tensor of shape [B (batch-size), num_masks, num_patches]
    returns: tensor of shape [B*num_masks, num of target tokens per sample per mask, D]
    """
    all_x = []   ## maintain a list for storing all 
    masks = masks.transpose(0, 1)  ## [B, num_masks, N] -> [num_masks, B, N]
    for m in masks:
        ## m is [B, N]
        # print("in apply_masks_targets: \n", "m.shape: ", m.shape, " x.shape: ", x.shape) ##[32, 200], [32, 200, 256]
        # mask_keep = m.unsqueeze(-1).repeat(1, 1, x.size(-1))
        # print("mask_keep.shape: ", mask_keep.shape)    ## [32, 200, 256]
        x_ = [x[i][m[i].bool()] for i in range(x.shape[0])]
        
        x_ = torch.stack(x_, dim=0)
        # print("x_.shape: ", x_.shape)    ## [32, 12, 256]
        # print(f"len(x_): {len(x_)}", "x_[0].shape: ", x_[0].shape)    ## [num of target tokens per sample per mask, D]
        all_x += [x_]
    all_x = torch.cat(all_x, dim=0)
    # print("all_x.shape: ", all_x.shape)    ## [32*4, 12, 256]
    return all_x

def apply_masks_indices(x, masks):
    """
    :param x: tensor of shape [num_indices, 1]  Boolean tensor
    :param masks: tensor of shape [B (batch-size), num_masks, num_patches]
    returns: tensor of shape [B*num_masks, num of target tokens per sample per mask, D]
    """
    x=x.unsqueeze(0)
    all_x = []   ## maintain a list for storing all 
    masks = masks.transpose(0, 1)  ## [B, num_masks, N] -> [num_masks, B, N]
    for m in masks:
        ## m is [B, N]
        # print("in apply_masks_targets: \n", "m.shape: ", m.shape, " x.shape: ", x.shape) ##[32, 200], [32, 200, 256]
        # mask_keep = m.unsqueeze(-1).repeat(1, 1, x.size(-1))
        # print("mask_keep.shape: ", mask_keep.shape)    ## [32, 200, 256]
        x_ = [x[i][m[i].bool()] for i in range(x.shape[0])]
        
        x_ = torch.stack(x_, dim=0)
        # print("x_.shape: ", x_.shape)    ## [32, 12, 256]
        # print(f"len(x_): {len(x_)}", "x_[0].shape: ", x_[0].shape)    ## [num of target tokens per sample per mask, D]
        all_x += [x_]
    all_x = torch.cat(all_x, dim=0)
    # print("all_x.shape: ", all_x.shape)    ## [32*4, 12, 256]
    return all_x


def init_opt(
    encoder,
    predictor,
    iterations_per_epoch,
    start_lr,
    ref_lr,
    warmup,
    num_epochs,
    wd=1e-6,
    final_wd=1e-6,
    final_lr=0.0,
    use_bfloat16=False,
    ipe_scale=1.25
):
    param_groups = [
        {
            'params': (p for n, p in encoder.named_parameters()
                       if ('bias' not in n) and (len(p.shape) != 1))
        }, {
            'params': (p for n, p in predictor.named_parameters()
                       if ('bias' not in n) and (len(p.shape) != 1))
        }, {
            'params': (p for n, p in encoder.named_parameters()
                       if ('bias' in n) or (len(p.shape) == 1)),
            'WD_exclude': True,
            'weight_decay': 0
        }, {
            'params': (p for n, p in predictor.named_parameters()
                       if ('bias' in n) or (len(p.shape) == 1)),
            'WD_exclude': True,
            'weight_decay': 0
        }
    ]

    logger.info('Using AdamW')
    optimizer = torch.optim.AdamW(param_groups)
    scheduler = WarmupCosineSchedule(
        optimizer,
        warmup_steps=int(warmup*iterations_per_epoch),
        start_lr=start_lr,
        ref_lr=ref_lr,
        final_lr=final_lr,
        T_max=int(ipe_scale*num_epochs*iterations_per_epoch))
    wd_scheduler = CosineWDSchedule(
        optimizer,
        ref_wd=wd,
        final_wd=final_wd,
        T_max=int(ipe_scale*num_epochs*iterations_per_epoch))
    scaler = torch.cuda.amp.GradScaler() if use_bfloat16 else None
    return optimizer, scaler, scheduler, wd_scheduler

class WarmupCosineSchedule(object):

    def __init__(
        self,
        optimizer,
        warmup_steps,
        start_lr,
        ref_lr,
        T_max,
        last_epoch=-1,
        final_lr=0.
    ):
        self.optimizer = optimizer
        self.start_lr = start_lr
        self.ref_lr = ref_lr
        self.final_lr = final_lr
        self.warmup_steps = warmup_steps
        self.T_max = T_max - warmup_steps
        self._step = 0.

    def step(self):
        self._step += 1
        if self._step < self.warmup_steps:
            progress = float(self._step) / float(max(1, self.warmup_steps))
            new_lr = self.start_lr + progress * (self.ref_lr - self.start_lr)
        else:
            # -- progress after warmup
            progress = float(self._step - self.warmup_steps) / float(max(1, self.T_max))
            new_lr = max(self.final_lr,
                         self.final_lr + (self.ref_lr - self.final_lr) * 0.5 * (1. + math.cos(math.pi * progress)))

        for group in self.optimizer.param_groups:
            group['lr'] = new_lr

        return new_lr


class CosineWDSchedule(object):

    def __init__(
        self,
        optimizer,
        ref_wd,
        T_max,
        final_wd=0.
    ):
        self.optimizer = optimizer
        self.ref_wd = ref_wd
        self.final_wd = final_wd
        self.T_max = T_max
        self._step = 0.

    def step(self):
        self._step += 1
        progress = self._step / self.T_max
        new_wd = self.final_wd + (self.ref_wd - self.final_wd) * 0.5 * (1. + math.cos(math.pi * progress))

        if self.final_wd <= self.ref_wd:
            new_wd = max(self.final_wd, new_wd)
        else:
            new_wd = min(self.final_wd, new_wd)

        for group in self.optimizer.param_groups:
            if ('WD_exclude' not in group) or not group['WD_exclude']:
                group['weight_decay'] = new_wd
        return new_wd