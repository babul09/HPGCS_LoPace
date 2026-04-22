# Technical Concerns

## Technical Debt
- **Missing Formal Test Suite**: Reliance on CLI simulation loads to assert deterministic behaviors lacks strict protection against modular regression down the line. Unit-testing the raw mathematical models for Centroid and Dictionary generation is advised.
- **Data Serialization Constraints**: Endpoints rely heavily on massive JSON blocks. Scaling into 10K+ nodes requires large chunks of unpaged memory bounds. 

## Known Issues
- Zstandard dictionary extraction overhead heavily masks compression ratio benefits natively on chunks experiencing less than uniform distribution bounds in zero-reuse conditions (e.g. going -130%+ compression scaling overhead relative to pure Brotli). 

## Fragile Areas
- `Adaptive Selector`: Currently triggers an expansive Oracle-tier sequential run attempting *all* compression targets simultaneously over iterations to derive an optimal outcome, which costs geometric runtime complexity against very large corpuses. Should be swapped out with a mathematical predictor matrix.
