import SwiftUI
import UIKit

@main
struct SMEtestApp: App {
  var body: some Scene {
    WindowGroup {
      MainView()
    }
  }
}

struct MainView: View {
  var body: some View {
    HStack {
      Spacer()
      Text("Running tests, please wait")
      ProgressView().scaleEffect(0.75)
      Spacer()
    }
    .padding()
    .task(priority: .utility) {
      UIApplication.shared.isIdleTimerDisabled = true
      runTests()

      // add a short delay to make sure that the console output has been flushed
      do {
        try await Task.sleep(for: .seconds(1))
      } catch {
        return
      }
      // tests are done, terminate the app
      exit(0)
    }
  }
}
