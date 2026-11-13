// Where does each operation of a Core ML model run? (MLComputePlan, macOS 14.4+)
// usage: mlplan <model.mlpackage | .mlmodel | .mlmodelc> [label]
// Prints, per compute-unit setting, the number of operations and the share of estimated cost
// whose PREFERRED device is the Neural Engine, the GPU or the CPU.
import CoreML
import Foundation

@main
struct MLPlan {
    static func main() async {
        let args = CommandLine.arguments
        guard args.count >= 2 else { print("usage: mlplan <model> [label]"); exit(2) }
        var url = URL(fileURLWithPath: args[1])
        let label = args.count > 2 ? args[2] : url.lastPathComponent
        if url.pathExtension != "mlmodelc" {
            do { url = try await MLModel.compileModel(at: url) }
            catch { print("\(label) | compile failed: \(error)"); return }
        }
        let settings: [(String, MLComputeUnits)] = [("cpuAndNeuralEngine", .cpuAndNeuralEngine),
                                                    ("cpuAndGPU", .cpuAndGPU), ("cpuOnly", .cpuOnly)]
        for (name, units) in settings {
            let config = MLModelConfiguration()
            config.computeUnits = units
            do {
                let plan = try await MLComputePlan.load(contentsOf: url, configuration: config)
                var ops = [String: Int](), cost = [String: Double]()
                var total = 0, totalCost = 0.0
                func device(_ d: MLComputeDevice) -> String {
                    switch d {
                    case .cpu: return "CPU"
                    case .gpu: return "GPU"
                    case .neuralEngine: return "NE"
                    @unknown default: return "other"
                    }
                }
                func walk(_ list: [MLModelStructure.Program.Operation]) {
                    for op in list {
                        if let usage = plan.deviceUsage(for: op) {
                            let d = device(usage.preferred)
                            let w = plan.estimatedCost(of: op)?.weight ?? 0
                            ops[d, default: 0] += 1; cost[d, default: 0] += w
                            total += 1; totalCost += w
                        }
                        for b in op.blocks { walk(b.operations) }
                    }
                }
                switch plan.modelStructure {
                case .program(let program):
                    for (_, f) in program.functions { walk(f.block.operations) }
                default:
                    print("\(label) | \(name) | not an ML program: per-operation plan unavailable"); continue
                }
                let parts = ["NE", "GPU", "CPU"].map { d -> String in
                    let share = totalCost > 0 ? 100 * cost[d, default: 0] / totalCost : 0
                    return "\(d) \(ops[d, default: 0]) ops \(String(format: "%.1f", share))% cost"
                }
                print("\(label) | \(name) | \(total) ops | " + parts.joined(separator: " | "))
            } catch {
                print("\(label) | \(name) | plan failed: \(error)")
            }
        }
    }
}
