#include "bench.h"

#include <sys/qos.h>
#include <pthread.h>
#include <stdatomic.h>
#include <assert.h>
#include <stdio.h>
#include <dispatch/dispatch.h>

#define QUEUE_QOS(qos) dispatch_queue_attr_make_with_qos_class(DISPATCH_QUEUE_CONCURRENT, qos, 0)

benchmark_result_t run_benchmark(
  const benchmark_t* __nonnull bench,
  const void* __nullable params,
  size_t n_threads_highp,
  size_t n_threads_lowp
) {
  assert(n_threads_highp + n_threads_lowp > 0);
  __block _Atomic double total_ops = 0.0;
  __block _Atomic bool ready = false;

  void* task_data[n_threads_highp + n_threads_lowp];

  // create queues (low-priority threads run with utility QoS, which should place them on E-cores)
  dispatch_queue_t queue_highp = dispatch_queue_create("SMETest high-priority queue", QUEUE_QOS(QOS_CLASS_USER_INITIATED));
  dispatch_queue_t queue_lowp = dispatch_queue_create("SMETest low-priority  queue", QUEUE_QOS(QOS_CLASS_UTILITY));
  dispatch_suspend(queue_highp);
  dispatch_suspend(queue_lowp);

  // setup and schedule the tasks
  dispatch_group_t group = dispatch_group_create();
  for (size_t i = 0; i < n_threads_highp + n_threads_lowp; i++) {
    void* data = task_data[i] = bench->setup(params);

    dispatch_group_async(
      group,
      (i < n_threads_highp) ? queue_highp : queue_lowp,
      ^{
        while (!ready) {} // block until timing starts
        double ops = bench->bench(data);
        atomic_fetch_add_explicit(&total_ops, ops, memory_order_relaxed);
      }
    );
  }

  // run the benchmarks
  dispatch_resume(queue_highp);
  dispatch_resume(queue_lowp);

  uint64_t t0 = clock_gettime_nsec_np(CLOCK_UPTIME_RAW);
  ready = true;
  dispatch_group_wait( group, DISPATCH_TIME_FOREVER );
  uint64_t t1 = clock_gettime_nsec_np(CLOCK_UPTIME_RAW);

  double elapsed = (double)(t1 - t0)/1e9;

  dispatch_release(queue_highp);
  dispatch_release(queue_lowp);

  for (size_t i = 0; i < n_threads_highp + n_threads_lowp; i++) {
    bench->teardown(task_data[i]);
  }

  return (benchmark_result_t) { .elapsed = elapsed, .total_ops = total_ops };
}
