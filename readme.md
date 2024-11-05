# Exploring SME performance of Apple M4

## Introduction

The 2024 iPad Pro, featuring the Apple M4 chip, is the first device available to the public that supports ARM's scalable matrix extension (SME). Although Apple has included a matrix accelerator in its devices since 2019, it used a proprietary instruction set called AMX[^1]. The developers had to use Apple-provided numerical frameworks to take advantage of the hardware. The M4 chip with SME changes this by allowing programmers to write low-level code that directly targets the matrix hardware, bringing potential performance improvements to scientific and machine learning algorithms.

My investigation aims to explore the M4 SME hardware and study the SME instruction set. I am particularly interested in how these features can be used to accelerate vector operations. The initial experiments study the peak compute throughput for common matrix and vector operations and the memory transfer rates using various methods. My methodology relies on generating multiple variants of microbenchmark code over a wide range of parameters and studying the results (see the Python code in `tools/` for how the benchmarks are generated). I expect to extend this project as new aspects of the hardware are tested. Pull requests and commentary are welcome!

Another in-depth investigation of M4 SME is provided by a team at the University of Jena, who are building a high-performance GEMM implementation [^2]. It is an excellent read if you are interested in the topic.

[^1]: [https://github.com/corsix/amx](https://github.com/corsix/amx) -  description of Apple proprietary AMX extensions
[^2]: [https://scalable.uni-jena.de/opt/sme/](https://scalable.uni-jena.de/opt/sme/)

## Contents

- [A brief overview of SME in Apple M4](reports/01-sme-overview.md)
- [Outer Product Microbenchmarks](reports/02-sme-outer-product.md)

### Running the tests

#### Requirements

- An M4 iPad Pro with Developer Mode activated and paired with your Mac
- Apple Xcode with installed Command Line Tools
- [XcodeGen](https://github.com/yonaskolb/XcodeGen) (`brew install xcodegen`)
- Python3 with PyYAML package to generate the tests
- [Quarto](https://quarto.org)+R/tidyverse to render the reports

Note: this project currently only runs on an external M4 iPad Pro. As M4 Macs are expected to be available soon, it would be desirable to run these tests locally. Pull requests are welcome!

#### Building and running

After downloading or cloning the project, perform the following steps

```bash
# setup a paired M4 iPad and the code signing information
./setup
# compile the project and install it on the iPad
make build
# run the tests — this will take a while!
make run
# copy the benchmark results
make copy_results
```

After the testing is done, the generated JSON reports are copied from the iPad and placed in the `results/` folder. If you have R and Quarto installed, you can also build the R-Markdown reports using `make reports`.

By default, both single-core and multi-core tests are executed. This can take a long time. If you are only interested in peak single-core rates, you can change the second line in `src/tests.swift` from `let multiCoreTests = true` to `false` and rebuild.
