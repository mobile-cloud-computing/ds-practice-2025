import jax
from transformers import AutoTokenizer, FlaxBertForMultipleChoice

# _DEFAULT_MODEL = "bert-base-uncased"
_DEFAULT_MODEL = "distilbert-base-uncased"


class FraudDetectionModel:
    def __init__(self, model_name=_DEFAULT_MODEL):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, resume_download=True)
        self.mc_model = FlaxBertForMultipleChoice.from_pretrained(
            model_name,
            resume_download=True,
            output_attentions=True,
            output_hidden_states=True,
        )

    def check_fraud(self, input):
        fraud = "Fraud"
        not_fraud = "Not Fraud"
        choices = [fraud, not_fraud]
        input = [input] * len(choices)
        encoding = self.tokenizer(
            input, choices, return_tensors="jax", padding=True, truncation=True
        )
        outputs = self.mc_model(**{k: v[None, :] for k, v in encoding.items()})
        probs = jax.nn.softmax(outputs.logits, axis=-1)
        probs_list = probs.tolist()[0]
        mapped = {choice: prob for choice, prob in zip(choices, probs_list)}
        is_fraud = mapped[fraud] > (mapped[not_fraud] + 0.1)
        return {
            "is_fraud": is_fraud,
            "probabilities": {"fraud": mapped[fraud], "not_fraud": mapped[not_fraud]},
        }
