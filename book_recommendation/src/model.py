import jax
from transformers import AutoTokenizer, FlaxBertForMultipleChoice

_DEFAULT_DISTILBERT_MODEL = "distilbert-base-uncased"


class BookRecommendationModel:
    def __init__(self):
        self.model_name = _DEFAULT_DISTILBERT_MODEL
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, resume_download=True)
        self.mc_model = FlaxBertForMultipleChoice.from_pretrained(
            self.model_name,
            resume_download=True,
            output_attentions=True,
            output_hidden_states=True,
        )

    def recommend(self, prompt, choices):
        prompt = [prompt] * len(choices)
        encoding = self.tokenizer(
            prompt, choices, return_tensors="jax", padding=True, truncation=True
        )
        outputs = self.mc_model(**{k: v[None, :] for k, v in encoding.items()})
        probs = jax.nn.softmax(outputs.logits, axis=-1)
        probs_list = probs.tolist()[0]
        mapped = {choice: prob for choice, prob in zip(choices, probs_list)}
        return sorted(mapped.items(), key=lambda x: x[1], reverse=True)[:2]
