#ifndef tests_h
#define tests_h

#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>

#define CONST_PTR(T) const T* __nonnull
#define ARRAY_END(x) (x + sizeof(x)/sizeof(x[0]))


// Benchmarking harness
//
// A benchmark consists of three entry points: a setup function that performs nessesary
// allocations and preprocessing, a teardown function that cleans up the state, and the
// benchmark function proper. The benchmarking function returns the number of executed
// operations (benchmark-dependent) as a double.
//
// These entry points are stored as a `struct benchmark_t`.
//
// The `run_benchmark()` function accepts a benchmark definition and executes it using
// the requested number of threads. The result consists of a number of total executed
// operations (benchmark-dependent) and the combined runtime.

// Benchmark definition
typedef struct {
  // setup the benchmark adata
  void* __nullable  (*__nonnull setup)(const void* __nullable);
  // run the benchmark and return the number of operations executed
  double (*__nonnull bench)(const void* __nullable);
  // teardown the benchmark data
  void   (*__nonnull teardown)(void* __nullable);
} benchmark_t;

// Benchmark result
typedef struct {
  // elapsed time
  double elapsed;
  // number of operations executed
  double total_ops;
} benchmark_result_t;

// Run the provided benchmark using one or more threads
benchmark_result_t run_benchmark(
  // benchmark to run
  const benchmark_t* __nonnull bench,
  // benchmark parameters (benchmark-dependent)
  const void* __nullable params,
  // number of high-priority threads to run
  size_t n_threads_highp,
  // number of low-priority threads to run
  size_t n_threads_lowp
);

// SME and SVE instruction benchmarks
typedef struct {
  // benchmark harness
  const benchmark_t benchmark;
  // operation class of operation (e.g. outer product, vector)
  CONST_PTR(char)   category;
  // descriptive label
  CONST_PTR(char)   label;
  // required SVE/SME feature
  CONST_PTR(char)   feature;
  // instruction encoding (e.g. za-tile, za-vector)
  CONST_PTR(char)   encoding;
  // ARM opcode
  CONST_PTR(char)   opcode;
  // output element type (e.g. f32, i32)
  CONST_PTR(char)   output_data;
  // number of total elements in the output
  size_t            output_elements;
  // number of VL-sized vectors in the output
  size_t            output_vectors;
  // input element type (e.g. f32, i32)
  CONST_PTR(char)   input_data;
  // number of total elements in the input
  size_t            input_elements;
  // number of VL-sized vectors in the input
  size_t            input_vectors;
  // total number of operations per instruction
  size_t            ops_per_instruction;
  // number of data-independent instructions in the benchmark loop
  size_t            ilp;
} op_benchmark_t;

extern CONST_PTR(op_benchmark_t) op_benchmarks;
extern const size_t op_benchmarks_count;


// Memory benchmarks
typedef struct {
  size_t size;
  size_t alignment;
} mem_benchmark_params_t;

typedef struct {
  // benchmark harness
  const benchmark_t benchmark;
  // descriptive label
  CONST_PTR(char)   label;
  // instruction encoding (e.g. za-vector, reg-adjacent)
  CONST_PTR(char)   encoding;
  // required SVE/SME feature
  CONST_PTR(char)   feature;
  // Operation type (load, store, copy)
  CONST_PTR(char)   op_type;
  // number of VL-sized vectors transferred per instruction
  size_t            n_vectors;
  // element bit width, -1 if untyped
  size_t            data_size;
  // number of data-independent instructions in the benchmark loop
  size_t            ilp;
} mem_benchmark_t;

extern CONST_PTR(mem_benchmark_t) mem_benchmarks;
extern const size_t mem_benchmarks_count;

extern CONST_PTR(op_benchmark_t) mixed_benchmarks;
extern const size_t mixed_benchmarks_benchmarks_count;


#endif /* tests_h */
