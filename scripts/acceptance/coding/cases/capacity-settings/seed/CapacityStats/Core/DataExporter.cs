using System.Globalization;
using System.Text;

namespace CapacityStats;

/// <summary>导出结果：写出的文件绝对路径。</summary>
public sealed record ExportResult(string Directory, string CapacityCsvPath, string FaultsCsvPath, int CapacityRows, int FaultRows);

/// <summary>
/// 信息导出：读取数据库并写出 capacity.csv / faults.csv。
/// </summary>
public static class DataExporter
{
    public static ExportResult Export(CapacityRepository repository, string outputDirectory)
    {
        var dir = Path.GetFullPath(outputDirectory);

        var capacityDays = repository.LoadCapacityRange(PageStats.ExportStartDate, PageStats.ExportEndDate);
        var capacityRows = PageStats.BuildCapacityCsvRows(capacityDays);
        var capacityCsv = CsvWriter.Build(PageStats.CapacityCsvHeader, capacityRows);

        var infoRows = repository.LoadFaultInfoRows();
        var faultRows = PageStats.BuildFaultsCsvRows(infoRows);
        var faultsCsv = CsvWriter.Build(PageStats.FaultsCsvHeader, faultRows);

        var capacityPath = Path.Combine(dir, PageStats.CapacityCsvName);
        var faultsPath = Path.Combine(dir, PageStats.FaultsCsvName);
        CsvWriter.WriteFile(capacityPath, capacityCsv);
        CsvWriter.WriteFile(faultsPath, faultsCsv);

        return new ExportResult(dir, capacityPath, faultsPath, capacityRows.Count, faultRows.Count);
    }

    /// <summary>命令行 --export 的输出文本。</summary>
    public static string Describe(ExportResult result)
    {
        var sb = new StringBuilder();
        sb.AppendLine("EXPORT " + result.Directory);
        sb.AppendLine($"{PageStats.CapacityCsvName} {result.CapacityCsvPath} rows={result.CapacityRows.ToString(CultureInfo.InvariantCulture)}");
        sb.AppendLine($"{PageStats.FaultsCsvName} {result.FaultsCsvPath} rows={result.FaultRows.ToString(CultureInfo.InvariantCulture)}");
        return sb.ToString();
    }
}
