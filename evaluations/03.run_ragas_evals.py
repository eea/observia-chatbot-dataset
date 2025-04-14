import json
import os

from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.together import TogetherLLM

from ragas import evaluate, SingleTurnSample, EvaluationDataset
from ragas.embeddings import LlamaIndexEmbeddingsWrapper  # LangchainEmbeddingsWrapper
from ragas.llms import LlamaIndexLLMWrapper
from ragas.metrics import  Faithfulness, LLMContextPrecisionWithoutReference, ResponseRelevancy


from utils import load_jsonl

from dotenv import load_dotenv
load_dotenv()


jsons_folder = os.environ.get('JSONS_FOLDER', 'tmp')

ragas_embed_host = os.environ.get("RAGAS_EMBED_HOST")
ragas_embed_key = os.environ.get("RAGAS_EMBED_KEY")
ragas_embed_model = os.environ.get("RAGAS_EMBED_MODEL")

ragas_llm_host = os.environ.get("RAGAS_LLM_HOST")
ragas_llm_key = os.environ.get("RAGAS_LLM_KEY")
ragas_llm_model = os.environ.get("RAGAS_LLM_MODEL")


def init_metrics():
    embedding_model_params = {
        "api_key": ragas_embed_key,
        "api_base": ragas_embed_host,
        "model_name": ragas_embed_model
    }
    embeddings = OpenAIEmbedding(**embedding_model_params)
    evaluator_embeddings = LlamaIndexEmbeddingsWrapper(embeddings)

    llm_model_params = {
        "api_key": ragas_llm_key,
        "base_url": ragas_llm_host,
        "model": ragas_llm_model
    }

    chat_model = TogetherLLM(**llm_model_params)

    evaluator_llm = LlamaIndexLLMWrapper(chat_model)
    ff = Faithfulness()
    rr = ResponseRelevancy(embeddings = evaluator_embeddings)
    cpw = LLMContextPrecisionWithoutReference()

    metrics = [ff, rr, cpw]
    return(metrics, evaluator_llm)


def eval_ragas(data, metrics, evaluator_llm):
    with open(os.path.join(jsons_folder,"03.ragas.jsonl"), "w") as f:
        cnt = 0
        for row in data:
            print(cnt)
            cnt+=1
            sample = SingleTurnSample(
                user_input=row['question'], 
                retrieved_contexts=row['contexts'], 
                response=row['answer']
            )
            eval_dataset = EvaluationDataset(samples=[sample])
            result = evaluate(dataset=eval_dataset, metrics=metrics, llm=evaluator_llm)
            res = {"question":row["question"],"faithfulness":result.scores[0]["faithfulness"], "answer_relevancy":result.scores[0]["answer_relevancy"],"llm_context_precision_without_reference":result.scores[0]["llm_context_precision_without_reference"]}
            f.write(json.dumps(res) + "\n")


if __name__ == "__main__":
    metrics, evaluator_llm = init_metrics()
    qas = load_jsonl(json.path.join(jsons_folder, "02.qa.jsonl"))
    import pdb; pdb.set_trace()
    eval_ragas(qas, metrics, evaluator_llm)