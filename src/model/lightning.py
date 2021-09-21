import pytorch_lightning as pl
from sklearn.metrics import f1_score


class LitClassifier(pl.LightningModule):
    def __init__(self, model, config):
        super().__init__()
        self.model = model
        self.lr = config.lr
        self.criterion = torch.nn.CrossEntropyLoss()

    def shared_step(self, batch, batch_idx, return_pred_labels=False):
        """
        this step will be shared by the train/val/test logic
        """
        out_dict = self.model(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
            return_dict=True,
        )
        logits = self.classifier(out_dict["pooler_output"])

        pred_labels = torch.argmax(logits, dim=1)
        actual_labels = batch["label"]

        loss = self.criterion(logits, actual_labels)

        # Logging to TensorBoard by default
        metrics = {}

        pred_labels = pred_labels.detach().cpu().numpy()
        actual_labels = actual_labels.detach().cpu().numpy()
        logits = logits.detach().cpu().numpy()

        metrics["loss"] = loss
        metrics["acc"] = (pred_labels == actual_labels).sum() / pred_labels.shape[0]
        metrics["macro_f1"] = f1_score(actual_labels, pred_labels, average="macro")
        metrics["weighted_f1"] = f1_score(
            actual_labels, pred_labels, average="weighted"
        )
        return_dict = {"loss": loss, "metrics": metrics}
        if return_pred_labels:
            return_dict["pred_labels"] = pred_labels
        return return_dict

    def training_step(self, batch, batch_idx):
        shared_step_out_dict = self.shared_step(batch, batch_idx)
        loss, metrics = shared_step_out_dict["loss"], shared_step_out_dict["metrics"]

        metrics = {"train_" + k: v for k, v in metrics.items()}
        self.log_dict(metrics, on_epoch=True, prog_bar=True, logger=True)
        return loss

    def validation_step(self, batch, batch_idx):
        shared_step_out_dict = self.shared_step(batch, batch_idx)
        loss, metrics = shared_step_out_dict["loss"], shared_step_out_dict["metrics"]

        metrics = {"val_" + k: v for k, v in metrics.items()}
        self.log_dict(metrics, on_epoch=True, prog_bar=True, logger=True)
        return loss

    def test_step(self, batch, batch_idx):
        shared_step_out_dict = self.shared_step(batch, batch_idx)
        loss, metrics = shared_step_out_dict["loss"], shared_step_out_dict["metrics"]

        metrics = {"test_" + k: v for k, v in metrics.items()}
        self.log_dict(metrics, on_epoch=True, prog_bar=True, logger=True)
        return loss

    def configure_optimizers(self):
        """
        defines optimizers and LR schedulers to be used by the trainer.
        """
        optimizer = torch.optim.Adam(self.parameters(), lr=self.lr)
        return optimizer