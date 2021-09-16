from src.data.consts import DEST_DATA_PKL_DIR
from math import ceil
import os
import pandas as pd
import torch


class HFDataset(torch.utils.data.Dataset):
    def __init__(self, df, tokenizer, max_seq_len):
        self.labels = df.label.tolist()
        self.encodings = tokenizer(
            df.text.tolist(),
            max_length=ceil(max_seq_len / 8) * 8,
            truncation=True,
            padding="max_length",
            pad_to_multiple_of=8,
        )

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item["label"] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)


def get_dataloader(dataset_name, split_name, config):

    pkl_path = os.path.join(DEST_DATA_PKL_DIR, f"{dataset_name}_{split_name}.pkl")
    data_df = pd.read_pickle(pkl_path, compression=None)
    if config.dataset_type == "bert":
        dataset = HFDataset(data_df, config.tokenizer, max_seq_len=config.max_seq_len)
    else:
        raise ValueError(f"Unknown dataset_type {dataset_type}")
    dataloader = torch.utils.data.DataLoader(
        dataset, batch_size=config.batch_size, num_workers=config.num_workers
    )

    return dataloader