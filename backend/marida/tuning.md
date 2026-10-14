# ResNet tuning

This is a small screening sweep for the MARIDA pixel segmenter. It changes residual depth, channel width, dropout, learning rate, weight decay, batch size, class weighting, and loss. Each run uses the official training and validation splits, and validation Marine Debris F1 selects the candidate. The official test split remains untouched.

The plan is printed as JSON with:

```sh
python -m backend.marida.scripts.tune_resnet --plan
```

Its entries follow this shape:

```json
{
  "layers": "1,1,1,1",
  "width": 8,
  "dropout": 0.2,
  "lr": 0.001,
  "weight_decay": 0.001,
  "batch_size": 8,
  "class_weight": "balanced",
  "loss": "cross_entropy"
}
```

`layers` gives residual block counts across the four encoder stages. This model is trained from scratch, so pretrained-block freezing is not applicable. The default plan has nine configurations, including shallow/deeper networks, two widths, cross-entropy/focal loss, and weighted/unweighted classes. It runs three epochs per configuration as an initial screen.

Run the sweep from the repository root:

```sh
python -m backend.marida.scripts.tune_resnet
```

The script ranks trials by validation F1, writes `outputs/resnet_tuning_summary.json`, and copies the winning checkpoint to `checkpoints/resnet_segmentation_tuned.pt`. This short screen identifies candidates; the selected configuration should be trained longer before the final one-time evaluation on MARIDA's held-out test split.

## Screening results

The completed three-epoch screen selected `resnet_tune_06`: one residual block per stage, width 16, dropout 0.2, learning rate `0.0003`, weight decay `0.001`, batch size 4, balanced class weights, and cross entropy. Its best validation precision was **0.093**, recall **0.410**, F1 **0.152**, and IoU **0.082**. RF-SS+SI scored validation F1 **0.870** on the same split.

Only this wider configuration and the deeper focal-loss configuration produced nonzero F1 in the three-epoch screen; all other candidates scored zero. This is too short to declare the ResNet fully tuned, and the selected candidate remains substantially behind the RF baseline. No test patches were used.
