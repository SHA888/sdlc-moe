# Model Assignments and Benchmarks

This document provides sources and citations for the model assignments used in sdlc-moe.

## Benchmark Sources

Model assignments are based on published benchmark data:

### Code Generation Benchmarks
- **SWE-bench**: https://github.com/princeton-nlp/SWE-bench
- **HumanEval**: https://github.com/openai/human-eval
- **LiveCodeBench**: https://github.com/LiveCodeBench/LiveCodeBench

### Model Performance Data

#### Qwen2.5-Coder Series
- **7B**: Strong on HumanEval (76.6%), efficient for 8-16GB RAM
- **32B**: Excellent SWE-bench performance (42.1%), requires 32GB+ RAM
- Source: https://qwenlm.github.io/blog/qwen2.5-coder/

#### DeepSeek Models
- **R1 14B**: Reasoning specialist, strong on algorithm tasks
- **Coder V2 16B**: Code completion specialist
- Source: https://github.com/deepseek-ai

#### Phi-4 14B
- Microsoft's instruction-tuned model
- Strong on requirements and security tasks
- Source: https://huggingface.co/microsoft/Phi-4

#### Other Models
- **StarCoder2 15B**: Fill-in-the-middle specialist
- **Gemma 3 12B**: Documentation specialist
- **Mistral Small 3 24B**: Balanced generalist
- **Llama3.3 70B**: Largest available, for extended tier

## Citation Format

When adding model assignments, include:
- Benchmark name and score
- Source link
- Reason for phase assignment

Example:
```
- Phase: Requirements
- Model: Phi-4 14B
- Benchmarks: HumanEval 78.2%, MMLU 68.9%
- Source: https://huggingface.co/microsoft/Phi-4
- Reasoning: Strong instruction following, good at requirement elicitation
```
