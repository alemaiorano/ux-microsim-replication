# Amazon Appstore baseline eval

- sample_n: 500
- labels: compatibility_device, functionality_features, performance_stability, security_privacy, support_responsiveness, ui_ux, other

## Results

- majority: acc=0.432 macro_f1=0.086 (label=functionality_features)
- lexical: acc=0.424 macro_f1=0.366
- tfidf_logreg_cv: acc=0.492 macro_f1=0.146 (folds=5)
- ollama_embed_logreg_cv: acc=0.635 macro_f1=0.336 (model=nomic-embed-text, used=200/500, folds=5)
