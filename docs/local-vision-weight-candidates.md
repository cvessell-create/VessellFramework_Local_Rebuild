# Local vision weight candidates: research, not an installed verifier

Public metadata, model cards, license documents and HTTP file headers were
checked during the static-capture implementation. No weights were downloaded,
no ONNX graphs were executed and no inference latency or RAM benchmark was
measured. File sizes below are reported distribution sizes, not runtime memory.

| Candidate | Actual ONNX distribution found | Reported size | Appropriate bounded use |
| --- | --- | --- | --- |
| CLIP ViT-B/32 | Jina clip-as-service S3 `visual.onnx` and `textual.onnx` | 351,519,609 + 254,120,034 bytes | Optional image/text embedding similarity; not an intent verdict |
| RapidOCR / PaddleOCR exports | SWHL/RapidOCR detector and recognizer files | English detector 2,423,224 bytes; Chinese v4 detector 4,745,517; Chinese v4 recognizer 10,857,958 | Screenshot text extraction; requires the matching language model, decoder and preprocessing |
| BLIP image-captioning base | ningpp ONNX vision encoder and text decoder | 344,590,705 + 645,815,945 bytes | Hypothesis-generating captions, with autoregressive token generation |

## Sources and pins

- [OpenAI CLIP source/license](https://github.com/openai/CLIP/blob/b1c4b6be5871f1b94359ba55901627f29ecc9ae9/LICENSE)
  declares MIT. The [Jina exporter/host project license](https://github.com/jina-ai/clip-as-service/blob/8681b88eb3a7806c1286eaefff3bd8a8ab28ff03/LICENSE)
  declares Apache-2.0 with MIT exceptions. Its
  [visual weight object](https://clip-as-service.s3.us-east-2.amazonaws.com/models/onnx/ViT-B-32/visual.onnx)
  and [text weight object](https://clip-as-service.s3.us-east-2.amazonaws.com/models/onnx/ViT-B-32/textual.onnx)
  are unversioned third-party objects, not an immutable OpenAI release.
- [RapidOCR files at revision `1cfba2e90fc938db55889873735088de210cc173`](https://huggingface.co/SWHL/RapidOCR/tree/1cfba2e90fc938db55889873735088de210cc173)
  include `PP-OCRv4/en_PP-OCRv3_det_infer.onnx`,
  `PP-OCRv4/ch_PP-OCRv4_det_infer.onnx` and
  `PP-OCRv4/ch_PP-OCRv4_rec_infer.onnx`. The model card declares Apache-2.0;
  the repository did not include a separate license file in the inspected
  listing. The [PaddleOCR source license](https://github.com/PaddlePaddle/PaddleOCR/blob/b9da97bea9db53ea5cbb1c32bf5c53b9d09be7b1/LICENSE)
  is Apache-2.0. The English detector is not by itself an English recognizer.
- [BLIP ONNX files at revision `3bc5068f59dad3619e29e5283a41632b101ab8ae`](https://huggingface.co/ningpp/blip-image-captioning-base-ONNX/tree/3bc5068f59dad3619e29e5283a41632b101ab8ae)
  include `blip_vision_encoder.onnx` and `blip_text_decoder.onnx`.
  Its model card declares BSD-3-Clause, but no separate license file or
  documented conversion recipe was found in that listing.
  [Salesforce's source license](https://github.com/salesforce/BLIP/blob/d6643642428fde32a9572d60392cbe71789f5858/LICENSE.txt)
  uses BSD-3-Clause terms. The original Salesforce model distribution is
  not itself an ONNX export.

Code licenses and model-card declarations are evidence to review, not an
independent audit of third-party binary provenance or redistribution rights.
Before bundling any export, confirm applicable weight terms and notices,
provenance, a content SHA-256 and the precise preprocessing/graph contract.

## Recommendation and adoption gate

Keep the working [deterministic capture path](static-artifact-capture.md)
as the release default. CLIP is a reasonable *optional similarity experiment*
if that metric is wanted; RapidOCR is much smaller and better aligned with a
separate screenshot-text extraction experiment. Neither adds a correctness
guarantee to the existing DOM checks. BLIP is less directly suited to this
bounded task and still generates tokens; ONNX does not make it tokenless.

An adapter should not activate until all of these are recorded:

1. Selected repository revision or immutable artifact and SHA-256.
2. Reviewed weight licensing/provenance and required redistribution notices.
3. Actual graph input/output names, shapes and dtypes; image normalization,
   tokenization or OCR decoding and dependency versions.
4. Bounded CPU execution and explicit missing-model/error states.
5. A local labeled evaluation against the intended metric, including false
   positives, false negatives, text-heavy screenshots and viewport changes.
6. Findings labeled as model hypotheses with human review, never automatic
   approval or execution authority.

The bounded search did not identify a ready-made trained model that verifies
arbitrary code diffs against rendered intent. That is not a claim that none
exists anywhere. No candidate supports constant-time, identical-across-hardware,
infinite-scale or zero-compute assertions. This release therefore keeps
`model_status: not_configured`.
