import Foundation

extension Array where Element == Double {
  func median() -> Double {
    guard !self.isEmpty else { return 0.0 }
    let sorted = self.sorted()
    let mid = sorted.count / 2
    if sorted.count.isMultiple(of: 2) {
      return (sorted[mid - 1] + sorted[mid]) / 2.0
    } else {
      return sorted[mid]
    }
  }
}

func writeReport(_ data: Codable, to file: String) {
  // prepare the output directory
  let uri = try! FileManager.default
    .url(for: .documentDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
    .appendingPathComponent("SMETest")

  try! FileManager.default.createDirectory(at: uri, withIntermediateDirectories: true)

  // write the data
  let encoder = JSONEncoder()
  encoder.outputFormatting = .prettyPrinted

  let json = try! encoder.encode(data)
  try! json.write(to: uri.appendingPathComponent(file), options: .atomic)
}

extension Double {
  func rounded(to places: Int) -> Double {
    let scale = pow(10.0, Double(places))
    return (self * scale).rounded() / scale
  }
}

extension String {
  func padding(to: Int, right: Bool = true) -> String {
    guard self.count < to else { return self }
    if right {
      return self.padding(toLength: to, withPad: " ", startingAt: 0)
    } else {
      var out = self
      while out.count < to { out = " " + out }
      return out
    }
  }
}
