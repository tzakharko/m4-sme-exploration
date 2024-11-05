import Foundation

let multiCoreTests = true
let tests = ["memory", "ops"]

func runTests() {
  print("\u{001B}[0;36m-- CPU info\u{001B}[0m")
  let cpu_info = CPUInfo()
  print(cpu_info)
  writeReport(cpu_info, to: "cpu_info.json")
  let threadCombinations = cpu_info.getThreadCombinations()

  // SME/SVE operation benchmarks
  if tests.contains("ops") {
    print("\u{001B}[0;36m-- SME/SVE operations\u{001B}[0m\n")
    let results = OpBenchmark.runAllBenchmarks(threads: threadCombinations)
    writeReport(results, to: "op_benchmarks.json")
  }

  // memory benchmarks
  if tests.contains("memory") {
    print("\u{001B}[0;36m-- Memory benchmarks  (one thread) \u{001B}[0m\n")
    let results = MemoryBenchmark.runHarness(
      threads: [(1, 0), (0, 1)],
      // 4KB to 64MB (switching to multiplicative increases every 4 steps)
      sizes: MemoryBenchmark.generateTestSizes(4096, linear: 4, multiplicative: 5),
      alignments: [16, 32, 64, 128, 256]
    )
    writeReport(results, to: "mem_benchmarks.json")
  }
}

func runMicrobenchmark(
  _ bench: benchmark_t,
  params: UnsafeRawPointer?,
  threads: (Int, Int),
  times: Int,
  warmup: Int = 2
) -> [(elapsed: Double, total_ops: Double)] {
  var results: [(elapsed: Double, total_ops: Double)] = []
  //var elapsed: [Double] = []
  for i in 0..<times + warmup {
    let result = withUnsafePointer(to: bench) { run_benchmark($0, params, threads.0, threads.1) }
    if i >= warmup {
      results.append((elapsed: result.elapsed, total_ops: result.total_ops))
    }
  }
  return results
}

// CPU info
struct CPUInfo: Codable, CustomStringConvertible {
  let cpu_p_cores: Int
  let cpu_e_cores: Int
  let sme_features: [String]

  var cpu_cores: Int {
    return self.cpu_p_cores + self.cpu_e_cores
  }

  static let KNOWN_SME_FEATURES = [
    "FEAT_SME",
    "FEAT_SME2",
    "SME_F32F32",
    "SME_BI32I32",
    "SME_B16F32",
    "SME_F16F32",
    "SME_I8I32",
    "SME_I16I32",
    "FEAT_SME_F64F64",
    "FEAT_SME_I16I64",
  ]

  init() {
    // CPU configuration
    self.cpu_p_cores = Int(sysctl_get_int("hw.perflevel0.physicalcpu"))
    self.cpu_e_cores = Int(sysctl_get_int("hw.perflevel1.physicalcpu"))

    // SME features
    self.sme_features = Self.KNOWN_SME_FEATURES.filter({
      sysctl_get_int("hw.optional.arm." + $0) == 1
    })
  }

  var description: String {
    return """
      P-cores      \(self.cpu_p_cores)
      E-cores      \(self.cpu_e_cores)
      SME features \(self.sme_features.joined(separator: ", "))
      """
  }

  func getThreadCombinations() -> [(Int, Int)] {
    if multiCoreTests {
      return [
        // high-priority threads (p-cores and both)
        Array((1...self.cpu_cores).lazy.map({ ($0, 0) })),
        // e-cores only (low-priority threads)
        Array((1...self.cpu_e_cores).lazy.map({ (0, $0) })),
      ].flatMap({ $0 })
    } else {
      return [
        (1, 0),
        (0, 1),
      ]
    }
  }
}

struct OpBenchmark: Codable, CustomStringConvertible {
  // same as op_benchmark_t
  let category: String
  let label: String
  let feature: String
  let encoding: String
  let opcode: String
  let output_data: String
  let output_elements: Int
  let output_vectors: Int
  let input_data: String
  let input_elements: Int
  let input_vectors: Int
  let ops_per_instruction: Int
  let ilp: Int
  // number of threads (high-priority, low-priority)
  let threads_h: Int
  let threads_l: Int
  // estimated TOPs/second
  let gops: [Double]
  // median elapsed time
  let elapsed: Double

  static func runAllBenchmarks(
    threads: any Sequence<(Int, Int)>
  ) -> [Self] {
    var results: [Self] = []
    var skip: [String] = []

    let benchmarks = UnsafeBufferPointer(
      start: op_benchmarks,
      count: op_benchmarks_count
    )
    var last_category = ""

    let sme_features = CPUInfo().sme_features

    for bench in benchmarks {
      // skip unsupported tests
      let feature = String(cString: bench.feature)
      guard sme_features.contains(feature) else {
        let label = String(cString: bench.label)
        skip.append("* skipping test '\(label)' due to missing feature \(feature)")

        continue
      }

      // print a divider
      let category = String(cString: bench.category)
      if last_category != category {
        let hdr = "== \(category) ".padding(toLength: 52, withPad: "=", startingAt: 0)
        print("\n\u{001B}[0;36m\(hdr)\u{001B}[0m\n")
      }
      last_category = category

      // run the harness
      for threadCount in threads {
        let result = Self.runBenchmark(bench, threads: threadCount, times: 20)
        print(result)
        results.append(result)
      }
    }

    // print skipped tests
    if skip.count > 0 {
      skip = Array(Set(skip))

      print("")
      for test in skip {
        print(test)
      }
    }

    return results
  }

  static func runBenchmark(_ bench: op_benchmark_t, threads: (Int, Int), times: Int = 10) -> Self {
    let results = runMicrobenchmark(bench.benchmark, params: nil, threads: threads, times: times)

    return Self(
      category: String(cString: bench.category),
      label: String(cString: bench.label),
      feature: String(cString: bench.feature),
      encoding: String(cString: bench.encoding),
      opcode: String(cString: bench.opcode),
      output_data: String(cString: bench.output_data),
      output_elements: Int(bench.output_elements),
      output_vectors: Int(bench.output_vectors),
      input_data: String(cString: bench.input_data),
      input_elements: Int(bench.input_elements),
      input_vectors: Int(bench.input_vectors),
      ops_per_instruction: Int(bench.ops_per_instruction),
      ilp: Int(bench.ilp),
      threads_h: threads.0,
      threads_l: threads.1,
      gops: results.map({ $0.total_ops / $0.elapsed / 1e9 }),
      elapsed: results.map({ $0.elapsed }).median()
    )
  }

  var description: String {
    let label = self.label.padding(to: 50)
    let ilp = "ILP=\(self.ilp)".padding(to: 6)
    let vecs = "VLx\(self.output_vectors*self.ilp)".padding(to: 5)
    var gops = "\(self.gops.median().rounded(to: 2)) GOP/s".padding(to: 18, right: false)
    gops = "\u{001B}[0;32m\(gops)\u{001B}[0m"
    let threads = "\(self.threads_h)H+\(self.threads_l)L".padding(to: 6)
    let elapsed = "\((self.elapsed*1000).rounded(to: 2)) ms"

    return "\(label) | \(ilp) | \(vecs) | threads \(threads) | \(gops) (\(elapsed))"
  }
}

// SME Memcpy Benchmark
struct MemoryBenchmark: Codable, CustomStringConvertible {
  let label: String
  let encoding: String
  let feature: String
  let op_type: String
  let n_vectors: Int
  let data_size: Int
  let ilp: Int
  // memory buffer size and alignment (for each thread)
  let size: Int
  let alignment: Int
  // number of threads (high-priority, low-priority)
  let threads_h: Int
  let threads_l: Int
  // estimated TOPs/second
  let gbps: [Double]
  // median elapsed time
  let elapsed: Double

  static func runHarness(
    threads: any Sequence<(Int, Int)>,
    sizes: any Sequence<Int>,
    alignments: any Sequence<Int>
  ) -> [Self] {
    var results: [Self] = []
    var skip: [String] = []

    let benchmarks = UnsafeBufferPointer(
      start: mem_benchmarks,
      count: mem_benchmarks_count
    )
    var prev_test = ""
    let sme_features = CPUInfo().sme_features
    for bench in benchmarks {
      // skip unsupported tests
      let feature = String(cString: bench.feature)
      let label = String(cString: bench.label)
      guard sme_features.contains(feature) else {
        skip.append("* skipping test '\(label)' due to missing feature \(feature)")
        continue
      }

      // print a divider
      if prev_test != label {
        let hdr = "== \(label) ".padding(toLength: 52, withPad: "=", startingAt: 0)
        print("\n\u{001B}[0;36m\(hdr)\u{001B}[0m\n")
        prev_test = label
      }

      // run the harness
      let maxSize = sizes.max() ?? 0

      for size in sizes {
        for alignment in alignments {
          for threadCount in threads {
            // skip all tests that would allocate more than twice the maxSize in total
            guard (threadCount.0 + threadCount.1) * size <= 2 * maxSize else { continue }

            let result = Self.runBenchmark(
              bench,
              size: size,
              alignment: alignment,
              threads: threadCount,
              times: 10
            )
            print(result)
            results.append(result)
          }
        }
      }
    }

    print(skip.joined(separator: "\n"))
    return results
  }

  static func runBenchmark(
    _ bench: mem_benchmark_t,
    size: Int,
    alignment: Int,
    threads: (Int, Int),
    times: Int = 10
  ) -> Self {
    var params = mem_benchmark_params_t(size: size, alignment: alignment)
    let results = runMicrobenchmark(
      bench.benchmark,
      params: &params,
      threads: threads,
      times: 10
    )

    return Self(
      label: String(cString: bench.label),
      encoding: String(cString: bench.encoding),
      feature: String(cString: bench.feature),
      op_type: String(cString: bench.op_type),
      n_vectors: Int(bench.n_vectors),
      data_size: Int(bench.n_vectors),
      ilp: Int(bench.ilp),
      size: size,
      alignment: alignment,
      threads_h: threads.0,
      threads_l: threads.1,
      gbps: results.map({ $0.total_ops / $0.elapsed / 1e9 }),
      elapsed: results.map({ $0.elapsed }).median()
    )
  }

  var description: String {
    let label = self.label.padding(to: 40)
    let ilp = "ILP=\(self.ilp)".padding(to: 6)
    let vecs = "VLx\(self.n_vectors*self.ilp)".padding(to: 5)
    var tops = "\(self.gbps.median().rounded(to: 2)) GB/s".padding(to: 18, right: false)
    tops = "\u{001B}[0;32m\(tops)\u{001B}[0m"

    var size = ByteCountFormatter.string(fromByteCount: Int64(self.size), countStyle: .binary)
    size = size.padding(to: 8)
    let alignment = " @\(self.alignment)".padding(to: 5)
    let mem = "\(size) \(alignment)"

    let threads = "\(self.threads_h)H+\(self.threads_l)L".padding(to: 6)
    let elapsed = "\((self.elapsed*1000).rounded(to: 2)) ms"

    return "\(label) | \(ilp) | \(vecs) | \(mem) | threads \(threads) | \(tops) (\(elapsed))"
  }

  static func generateTestSizes(_ initial: Int, linear: Int, multiplicative: Int, max: Int? = nil)
    -> [Int]
  {
    // the step for each run is the run's first element
    var sizes: [Int] = []
    var step = initial
    for _ in 0..<multiplicative {
      sizes += (1...linear).map({ $0 * step })
      // move to the multiplicative step
      step = step * linear * 2
    }

    // filter by max size
    guard let max = max else { return sizes }
    return sizes.filter({ $0 <= max })
  }
}
