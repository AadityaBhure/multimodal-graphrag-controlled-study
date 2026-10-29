"""IEEE-style references (numbered in order of first citation by build_ieee.py).

Entries for the twelve method papers were checked against the PDFs in data/papers (authors, titles, venues, arXiv
identifiers). IEEE style lists up to six authors and uses "et al." beyond six.
"""
REFS = {
    # ------------------------------------------------------------------ RAG foundations
    'lewis2020': 'P. Lewis *et al.*, "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Proc. Adv. Neural Inf. Process. Syst. (NeurIPS)*, 2020, pp. 9459–9474.',
    'gao2023': 'Y. Gao *et al.*, "Retrieval-augmented generation for large language models: A survey," 2023, *arXiv:2312.10997*.',
    'liu2024lost': 'N. F. Liu *et al.*, "Lost in the middle: How language models use long contexts," *Trans. Assoc. Comput. Linguistics*, vol. 12, pp. 157–173, 2024.',
    'jiang2024longllmlingua': 'H. Jiang *et al.*, "LongLLMLingua: Accelerating and enhancing LLMs in long context scenarios via prompt compression," in *Proc. Annu. Meeting Assoc. Comput. Linguistics (ACL)*, 2024.',
    'jiang2023flare': 'Z. Jiang *et al.*, "Active retrieval augmented generation," in *Proc. Conf. Empirical Methods Natural Lang. Process. (EMNLP)*, 2023, pp. 7969–7992.',
    'asai2024selfrag': 'A. Asai, Z. Wu, Y. Wang, A. Sil, and H. Hajishirzi, "Self-RAG: Learning to retrieve, generate, and critique through self-reflection," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2024.',
    # ------------------------------------------------------------------ graph RAG
    'edge2024graphrag': 'D. Edge *et al.*, "From local to global: A graph RAG approach to query-focused summarization," 2024, *arXiv:2404.16130*.',
    'peng2024survey': 'B. Peng *et al.*, "Graph retrieval-augmented generation: A survey," 2024, *arXiv:2408.08921*.',
    'he2024gretriever': 'X. He *et al.*, "G-Retriever: Retrieval-augmented generation for textual graph understanding and question answering," in *Proc. Adv. Neural Inf. Process. Syst. (NeurIPS)*, 2024.',
    'zhu2025kg2rag': 'X. Zhu, Y. Xie, Y. Liu, Y. Li, and W. Hu, "Knowledge graph-guided retrieval augmented generation," 2025, *arXiv:2502.06864*.',
    'zhou2026qafd': 'Z. Zhou *et al.*, "Query-aware flow diffusion for graph-based RAG with retrieval guarantees," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2026.',
    'sun2024tog': 'J. Sun *et al.*, "Think-on-Graph: Deep and responsible reasoning of large language model on knowledge graph," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2024.',
    'gutierrez2024hipporag': 'B. J. Gutiérrez, Y. Shu, Y. Gu, M. Yasunaga, and Y. Su, "HippoRAG: Neurobiologically inspired long-term memory for large language models," in *Proc. Adv. Neural Inf. Process. Syst. (NeurIPS)*, 2024.',
    # ------------------------------------------------------------------ heterogeneous knowledge and fusion
    'oguz2022unikqa': 'B. Oguz *et al.*, "UniK-QA: Unified representations of structured and unstructured knowledge for open-domain question answering," in *Findings Assoc. Comput. Linguistics: NAACL*, 2022, pp. 1535–1546.',
    'jiang2023structgpt': 'J. Jiang, K. Zhou, Z. Dong, K. Ye, W. X. Zhao, and J.-R. Wen, "StructGPT: A general framework for large language model to reason over structured data," in *Proc. Conf. Empirical Methods Natural Lang. Process. (EMNLP)*, 2023, pp. 9237–9251.',
    'sarmah2024hybridrag': 'B. Sarmah, B. Hall, R. Rao, S. Patel, S. Pasquali, and D. Mehta, "HybridRAG: Integrating knowledge graphs and vector retrieval augmented generation for efficient information extraction," in *Proc. ACM Int. Conf. AI Finance (ICAIF)*, 2024.',
    'liang2024kag': 'L. Liang *et al.*, "KAG: Boosting LLMs in professional domains via knowledge augmented generation," 2024, *arXiv:2409.13731*.',
    'wu2026sag': 'Y. Wu *et al.*, "SAG: SQL-retrieval augmented generation with query-time dynamic hyperedges," 2026, *arXiv:2606.15971*.',
    'hsiao2025megarag': 'C.-H. Hsiao, Y.-C. Wang, T.-S. Lin, Y.-R. Yeh, and C.-S. Chen, "MegaRAG: Multimodal knowledge graph-based retrieval augmented generation," 2025, *arXiv:2512.20626*.',
    'bu2025qdmm': 'C. Bu *et al.*, "Query-driven multimodal GraphRAG: Dynamic local knowledge graph construction for online reasoning," in *Findings Assoc. Comput. Linguistics: ACL*, 2025, pp. 21360–21380.',
    # ------------------------------------------------------------------ adaptive and agentic retrieval
    'jeong2024adaptive': 'S. Jeong, J. Baek, S. Cho, S. J. Hwang, and J. C. Park, "Adaptive-RAG: Learning to adapt retrieval-augmented large language models through question complexity," in *Proc. Conf. North Amer. Chapter Assoc. Comput. Linguistics (NAACL)*, 2024.',
    'yan2024crag': 'S.-Q. Yan, J.-C. Gu, Y. Zhu, and Z.-H. Ling, "Corrective retrieval augmented generation," 2024, *arXiv:2401.15884*.',
    'agentg2025': 'Anonymous, "AGENT-G: An agentic framework for graph retrieval augmented generation," submitted to *Int. Conf. Learn. Represent. (ICLR)*, OpenReview, 2024. [Online]. Available: https://openreview.net/forum?id=g2C947jjjQ',
    'maharjan2026agent': 'A. Maharjan, D. Kaur, and R. G. Molyet, "Agent-orchestrated adaptive RAG: A comparative study on structured and multi-hop retrieval," 2026, *arXiv:2606.05658*.',
    'yao2023react': 'S. Yao *et al.*, "ReAct: Synergizing reasoning and acting in language models," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2023.',
    'trivedi2023ircot': 'H. Trivedi, N. Balasubramanian, T. Khot, and A. Sabharwal, "Interleaving retrieval with chain-of-thought reasoning for knowledge-intensive multi-step questions," in *Proc. Annu. Meeting Assoc. Comput. Linguistics (ACL)*, 2023, pp. 10014–10037.',
    # ------------------------------------------------------------------ data and benchmark
    'wu2024stark': 'S. Wu *et al.*, "STaRK: Benchmarking LLM retrieval on textual and relational knowledge bases," in *Proc. Adv. Neural Inf. Process. Syst. (NeurIPS), Datasets Benchmarks Track*, 2024.',
    'wang2020mag': 'K. Wang, Z. Shen, C. Huang, C.-H. Wu, Y. Dong, and A. Kanakia, "Microsoft Academic Graph: When experts are not enough," *Quant. Sci. Stud.*, vol. 1, no. 1, pp. 396–413, 2020.',
    # ------------------------------------------------------------------ models and systems
    'reimers2019sbert': 'N. Reimers and I. Gurevych, "Sentence-BERT: Sentence embeddings using Siamese BERT-networks," in *Proc. Conf. Empirical Methods Natural Lang. Process. Int. Joint Conf. Natural Lang. Process. (EMNLP-IJCNLP)*, 2019, pp. 3982–3992.',
    'wang2020minilm': 'W. Wang, F. Wei, L. Dong, H. Bao, N. Yang, and M. Zhou, "MiniLM: Deep self-attention distillation for task-agnostic compression of pre-trained transformers," in *Proc. Adv. Neural Inf. Process. Syst. (NeurIPS)*, 2020.',
    'johnson2021faiss': 'J. Johnson, M. Douze, and H. Jégou, "Billion-scale similarity search with GPUs," *IEEE Trans. Big Data*, vol. 7, no. 3, pp. 535–547, Jul. 2021.',
    'raasveldt2019duckdb': 'M. Raasveldt and H. Mühleisen, "DuckDB: An embeddable analytical database," in *Proc. ACM SIGMOD Int. Conf. Manage. Data*, 2019, pp. 1981–1984.',
    'raffel2020t5': 'C. Raffel *et al.*, "Exploring the limits of transfer learning with a unified text-to-text transformer," *J. Mach. Learn. Res.*, vol. 21, no. 140, pp. 1–67, 2020.',
    'nogueira2019monobert': 'R. Nogueira and K. Cho, "Passage re-ranking with BERT," 2019, *arXiv:1901.04085*.',
    'bajaj2016msmarco': 'P. Bajaj *et al.*, "MS MARCO: A human generated machine reading comprehension dataset," 2016, *arXiv:1611.09268*.',
    'xiao2024cpack': 'S. Xiao, Z. Liu, P. Zhang, N. Muennighoff, D. Lian, and J.-Y. Nie, "C-Pack: Packed resources for general Chinese embeddings," in *Proc. Int. ACM SIGIR Conf. Res. Develop. Inf. Retrieval (SIGIR)*, 2024.',
    'openai2025gptoss': 'OpenAI, "gpt-oss-120b & gpt-oss-20b model card," 2025, *arXiv:2508.10925*.',
    'ollama': 'Ollama, "Ollama: Get up and running with large language models locally," 2025. [Online]. Available: https://ollama.com',
    # ------------------------------------------------------------------ algorithms
    'platt1999': 'J. C. Platt, "Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods," in *Advances in Large Margin Classifiers*, A. J. Smola, P. Bartlett, B. Schölkopf, and D. Schuurmans, Eds. Cambridge, MA, USA: MIT Press, 1999, pp. 61–74.',
    'goemans1995': 'M. X. Goemans and D. P. Williamson, "A general approximation technique for constrained forest problems," *SIAM J. Comput.*, vol. 24, no. 2, pp. 296–317, 1995.',
    'hegde2015pcst': 'C. Hegde, P. Indyk, and L. Schmidt, "A nearly-linear time framework for graph-structured sparsity," in *Proc. Int. Conf. Mach. Learn. (ICML)*, 2015, pp. 928–937.',
    'kruskal1956': 'J. B. Kruskal, "On the shortest spanning subtree of a graph and the traveling salesman problem," *Proc. Amer. Math. Soc.*, vol. 7, no. 1, pp. 48–50, 1956.',
    'fountoulakis2020flow': 'K. Fountoulakis, D. Wang, and S. Yang, "p-Norm flow diffusion for local graph clustering," in *Proc. Int. Conf. Mach. Learn. (ICML)*, 2020, pp. 3222–3232.',
    # ------------------------------------------------------------------ statistics
    'holm1979': 'S. Holm, "A simple sequentially rejective multiple test procedure," *Scand. J. Statist.*, vol. 6, no. 2, pp. 65–70, 1979.',
    'efron1993': 'B. Efron and R. J. Tibshirani, *An Introduction to the Bootstrap*. New York, NY, USA: Chapman & Hall, 1993.',
    'cameron2008': 'A. C. Cameron, J. B. Gelbach, and D. L. Miller, "Bootstrap-based improvements for inference with clustered errors," *Rev. Econ. Statist.*, vol. 90, no. 3, pp. 414–427, 2008.',
    'good2005': 'P. Good, *Permutation, Parametric, and Bootstrap Tests of Hypotheses*, 3rd ed. New York, NY, USA: Springer, 2005.',
    'dror2018': 'R. Dror, G. Baumer, S. Shlomov, and R. Reichart, "The hitchhiker’s guide to testing statistical significance in natural language processing," in *Proc. Annu. Meeting Assoc. Comput. Linguistics (ACL)*, 2018, pp. 1383–1392.',
}
