import torch
from transformers import BertModel, XLMRobertaModel


class ClassificationHead(torch.nn.Module):
    def __init__(self, in_dim, out_dim, dropout_prob):
        super(ClassificationHead, self).__init__()
        self.ff1 = torch.nn.Linear(in_dim, in_dim // 2)
        self.dropout = torch.nn.Dropout(dropout_prob)
        self.ff2 = torch.nn.Linear(in_dim // 2, out_dim)

    def forward(self, in_tensor):
        return self.ff2(self.dropout(self.ff1(in_tensor)))


class XLMRClassifier(torch.nn.Module):
    def __init__(self, config):
        super(XLMRClassifier, self).__init__()
        self.lm = XLMRobertaModel.from_pretrained("xlm-roberta-base")
        self.classification_head = ClassificationHead(
            self.lm.config.hidden_size, 2, config.hp.dropout
        )

    def forward(self, batch):
        lm_out_dict = self.lm(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
            return_dict=True,
        )
        logits = self.classification_head(lm_out_dict["pooler_output"])
        return {"logits": logits}


class MBERTClassifier(torch.nn.Module):
    def __init__(self, config):
        super(MBERTClassifier, self).__init__()
        self.lm = BertModel.from_pretrained("bert-base-multilingual-uncased")
        self.classification_head = ClassificationHead(
            self.lm.config.hidden_size, 2, config.hp.dropout
        )

    def forward(self, batch):
        lm_out_dict = self.lm(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
            return_dict=True,
        )
        logits = self.classification_head(lm_out_dict["pooler_output"])
        return {"logits": logits}


class LSTMClassifier(torch.nn.Module):
    def __init__(self, config):
        super(LSTMClassifier, self).__init__()
        self.hidden_dim = config.hp.hidden_dim
        self.embeddings = torch.nn.Embedding.from_pretrained(torch.from_numpy(config.embeddings))
        self.lstm = torch.nn.LSTM(
            input_size=config.embeddings.shape[-1],
            hidden_size=self.hidden_dim,
            num_layers=config.hp.num_lstm_layers,
            batch_first=True,
            dropout=config.hp.dropout,
            bidirectional=True,
        )
        self.classification_head = ClassificationHead(
            2 * self.hidden_dim, 2, config.hp.dropout
        )

    def forward(self, batch):
        embedding_out = self.embeddings(batch["input_ids"])

        packed_input = torch.nn.utils.rnn.pack_padded_sequence(
            input=embedding_out.float(),
            lengths=batch["sequence_len"].tolist(),
            batch_first=True,
            enforce_sorted=False,
        )
        packed_out, _ = self.lstm(packed_input)
        output, _ = torch.nn.utils.rnn.pad_packed_sequence(packed_out, batch_first=True)

        lstm_out_forward = output[
            range(len(output)), batch["sequence_len"] - 1, : self.hidden_dim
        ]  # shape=(batch_size,hidden_dim,)
        lstm_out_backward = output[
            :, 0, self.hidden_dim :
        ]  # shape=(batch_size,hidden_dim,)
        lstm_out = torch.cat(
            [
                lstm_out_forward,
                lstm_out_backward,
            ],
            dim=-1,
        )  # shape=(batch_size,2*hidden_dim,)

        logits = self.classification_head(lstm_out)
        return {"logits": logits}
