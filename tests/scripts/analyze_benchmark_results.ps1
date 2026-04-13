param(
    [Parameter(Mandatory = $true)]
    [string]$ResultDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:TextConfigPath = Join-Path $PSScriptRoot "analyze_benchmark_results.zh-Hans.json"
$script:Texts = Get-Content -LiteralPath $script:TextConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

function To-Double {
    param([object]$Value)
    if ($null -eq $Value) { return 0.0 }
    $text = [string]$Value
    if ([string]::IsNullOrWhiteSpace($text)) { return 0.0 }
    return [double]::Parse($text, [System.Globalization.CultureInfo]::InvariantCulture)
}

function To-Int {
    param([object]$Value)
    if ($null -eq $Value) { return 0 }
    $text = [string]$Value
    if ([string]::IsNullOrWhiteSpace($text)) { return 0 }
    return [int]$text
}

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Escape-Xml {
    param([string]$Value)
    return [System.Security.SecurityElement]::Escape($Value)
}

function Get-MapValue {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Map,
        [Parameter(Mandatory = $true)]
        [string]$Key
    )

    $property = $Map.PSObject.Properties[$Key]
    if ($null -eq $property) {
        return $Key
    }
    return [string]$property.Value
}

function Get-SystemLabel {
    param([string]$Key)
    return Get-MapValue -Map $script:Texts.systems -Key $Key
}

function Get-ScenarioLabel {
    param([string]$Key)
    return Get-MapValue -Map $script:Texts.scenarios -Key $Key
}

function Get-FailureLabel {
    param([string]$Key)
    return Get-MapValue -Map $script:Texts.failures -Key $Key
}

function Get-CsvLabel {
    param([string]$Key)
    return Get-MapValue -Map $script:Texts.csv -Key $Key
}

function Get-Color {
    param(
        [double]$Value,
        [double]$MinValue,
        [double]$MaxValue,
        [int[]]$StartRgb,
        [int[]]$EndRgb
    )

    $ratio = 1.0
    if ($MaxValue -gt $MinValue) {
        $ratio = ($Value - $MinValue) / ($MaxValue - $MinValue)
    }
    if ($ratio -lt 0) { $ratio = 0 }
    if ($ratio -gt 1) { $ratio = 1 }

    $r = [int][math]::Round($StartRgb[0] + (($EndRgb[0] - $StartRgb[0]) * $ratio))
    $g = [int][math]::Round($StartRgb[1] + (($EndRgb[1] - $StartRgb[1]) * $ratio))
    $b = [int][math]::Round($StartRgb[2] + (($EndRgb[2] - $StartRgb[2]) * $ratio))
    return "#{0:X2}{1:X2}{2:X2}" -f $r, $g, $b
}

function Write-SvgBarChart {
    param(
        [string]$Path,
        [string]$Title,
        [string]$Subtitle,
        [array]$Rows,
        [string]$BaseColor = "#2563EB",
        [switch]$Gradient
    )

    $width = 960
    $height = 520
    $marginLeft = 90
    $marginRight = 40
    $marginTop = 70
    $marginBottom = 140
    $plotWidth = $width - $marginLeft - $marginRight
    $plotHeight = $height - $marginTop - $marginBottom
    $maxValue = [math]::Max(1.0, ($Rows | Measure-Object -Property value -Maximum).Maximum)
    $barCount = [math]::Max(1, $Rows.Count)
    $slotWidth = $plotWidth / $barCount
    $barWidth = [math]::Min(90, $slotWidth * 0.6)

    $svg = New-Object System.Collections.Generic.List[string]
    $svg.Add('<?xml version="1.0" encoding="UTF-8"?>')
    $svg.Add("<svg xmlns=""http://www.w3.org/2000/svg"" width=""$width"" height=""$height"" viewBox=""0 0 $width $height"">")
    $svg.Add('<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#111827}.title{font-size:24px;font-weight:700}.subtitle{font-size:13px}.label{font-size:12px}.value{font-size:12px;font-weight:600}.grid{stroke:#E5E7EB;stroke-width:1}.axis{stroke:#9CA3AF;stroke-width:1}</style>')
    $svg.Add('<rect width="100%" height="100%" fill="#FFFFFF"/>')
    $svg.Add("<text x=""$marginLeft"" y=""36"" class=""title"">$(Escape-Xml $Title)</text>")
    $svg.Add("<text x=""$marginLeft"" y=""58"" class=""subtitle"">$(Escape-Xml $Subtitle)</text>")

    foreach ($tick in 0..4) {
        $tickValue = $maxValue * $tick / 4.0
        $y = $marginTop + $plotHeight - ($plotHeight * $tick / 4.0)
        $svg.Add("<line x1=""$marginLeft"" y1=""$y"" x2=""$($marginLeft + $plotWidth)"" y2=""$y"" class=""grid"" />")
        $svg.Add("<text x=""$($marginLeft - 10)"" y=""$($y + 4)"" text-anchor=""end"" class=""label"">$([math]::Round($tickValue, 2))</text>")
    }

    $svg.Add("<line x1=""$marginLeft"" y1=""$marginTop"" x2=""$marginLeft"" y2=""$($marginTop + $plotHeight)"" class=""axis"" />")
    $svg.Add("<line x1=""$marginLeft"" y1=""$($marginTop + $plotHeight)"" x2=""$($marginLeft + $plotWidth)"" y2=""$($marginTop + $plotHeight)"" class=""axis"" />")

    for ($i = 0; $i -lt $Rows.Count; $i++) {
        $row = $Rows[$i]
        $value = [double]$row.value
        $heightValue = if ($maxValue -le 0) { 0 } else { $plotHeight * $value / $maxValue }
        $x = $marginLeft + ($slotWidth * $i) + (($slotWidth - $barWidth) / 2)
        $y = $marginTop + $plotHeight - $heightValue
        $fill = $BaseColor
        if ($Gradient) {
            $fill = Get-Color -Value $value -MinValue 0 -MaxValue $maxValue -StartRgb @(22, 163, 74) -EndRgb @(220, 38, 38)
        }
        $svg.Add("<rect x=""$x"" y=""$y"" width=""$barWidth"" height=""$heightValue"" rx=""6"" fill=""$fill"" />")
        $svg.Add("<text x=""$($x + ($barWidth / 2))"" y=""$([math]::Max($marginTop + 12, $y - 8))"" text-anchor=""middle"" class=""value"">$([math]::Round($value, 4))</text>")
        $anchorX = $x + ($barWidth / 2)
        $anchorY = $marginTop + $plotHeight + 18
        $svg.Add("<text x=""$anchorX"" y=""$anchorY"" text-anchor=""end"" transform=""rotate(-35 $anchorX $anchorY)"" class=""label"">$(Escape-Xml ([string]$row.label))</text>")
    }

    $svg.Add('</svg>')
    Set-Content -LiteralPath $Path -Value $svg -Encoding UTF8
}

function Write-SvgHeatmap {
    param(
        [string]$Path,
        [string]$Title,
        [string]$Subtitle,
        [string[]]$RowLabels,
        [string[]]$ColumnLabels,
        [array]$Values,
        [double]$MinValue,
        [double]$MaxValue,
        [int[]]$StartRgb,
        [int[]]$EndRgb
    )

    $cellWidth = 120
    $cellHeight = 46
    $marginLeft = 220
    $marginTop = 100
    $width = $marginLeft + ($cellWidth * $ColumnLabels.Count) + 60
    $height = $marginTop + ($cellHeight * $RowLabels.Count) + 120

    $svg = New-Object System.Collections.Generic.List[string]
    $svg.Add('<?xml version="1.0" encoding="UTF-8"?>')
    $svg.Add("<svg xmlns=""http://www.w3.org/2000/svg"" width=""$width"" height=""$height"" viewBox=""0 0 $width $height"">")
    $svg.Add('<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#111827}.title{font-size:24px;font-weight:700}.subtitle{font-size:13px}.label{font-size:12px}.value{font-size:12px;font-weight:600}</style>')
    $svg.Add('<rect width="100%" height="100%" fill="#FFFFFF"/>')
    $svg.Add("<text x=""24"" y=""36"" class=""title"">$(Escape-Xml $Title)</text>")
    $svg.Add("<text x=""24"" y=""58"" class=""subtitle"">$(Escape-Xml $Subtitle)</text>")

    for ($col = 0; $col -lt $ColumnLabels.Count; $col++) {
        $x = $marginLeft + ($col * $cellWidth) + ($cellWidth / 2)
        $svg.Add("<text x=""$x"" y=""84"" text-anchor=""middle"" class=""label"">$(Escape-Xml $ColumnLabels[$col])</text>")
    }

    for ($row = 0; $row -lt $RowLabels.Count; $row++) {
        $labelY = $marginTop + ($row * $cellHeight) + 29
        $svg.Add("<text x=""$($marginLeft - 10)"" y=""$labelY"" text-anchor=""end"" class=""label"">$(Escape-Xml $RowLabels[$row])</text>")

        for ($col = 0; $col -lt $ColumnLabels.Count; $col++) {
            $value = [double]$Values[$row][$col]
            $x = $marginLeft + ($col * $cellWidth)
            $y = $marginTop + ($row * $cellHeight)
            $fill = Get-Color -Value $value -MinValue $MinValue -MaxValue $MaxValue -StartRgb $StartRgb -EndRgb $EndRgb
            $textColor = "#111827"
            if ($value -ge ($MinValue + (($MaxValue - $MinValue) * 0.55))) {
                $textColor = "#FFFFFF"
            }
            $svg.Add("<rect x=""$x"" y=""$y"" width=""$cellWidth"" height=""$cellHeight"" rx=""4"" fill=""$fill"" stroke=""#FFFFFF"" stroke-width=""2"" />")
            $svg.Add("<text x=""$($x + ($cellWidth / 2))"" y=""$($y + 28)"" text-anchor=""middle"" class=""value"" fill=""$textColor"">$([math]::Round($value, 4))</text>")
        }
    }

    $legendX = 24
    $legendY = $height - 44
    $legendWidth = 240
    $legendHeight = 18
    for ($step = 0; $step -lt $legendWidth; $step++) {
        $value = $MinValue + (($MaxValue - $MinValue) * $step / [math]::Max(1, ($legendWidth - 1)))
        $fill = Get-Color -Value $value -MinValue $MinValue -MaxValue $MaxValue -StartRgb $StartRgb -EndRgb $EndRgb
        $svg.Add("<line x1=""$($legendX + $step)"" y1=""$legendY"" x2=""$($legendX + $step)"" y2=""$($legendY + $legendHeight)"" stroke=""$fill"" stroke-width=""1"" />")
    }
    $svg.Add("<rect x=""$legendX"" y=""$legendY"" width=""$legendWidth"" height=""$legendHeight"" fill=""none"" stroke=""#9CA3AF"" stroke-width=""1"" />")
    $svg.Add("<text x=""$legendX"" y=""$($legendY + 34)"" class=""label"">$([math]::Round($MinValue, 2))</text>")
    $svg.Add("<text x=""$($legendX + $legendWidth)"" y=""$($legendY + 34)"" text-anchor=""end"" class=""label"">$([math]::Round($MaxValue, 2))</text>")
    $svg.Add('</svg>')

    Set-Content -LiteralPath $Path -Value $svg -Encoding UTF8
}

function New-MarkdownTable {
    param(
        [string[]]$Headers,
        [array]$Rows
    )

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("| " + ($Headers -join " | ") + " |")
    $lines.Add("| " + (($Headers | ForEach-Object { "---" }) -join " | ") + " |")
    foreach ($row in $Rows) {
        $lines.Add("| " + ($row -join " | ") + " |")
    }
    return $lines
}

$resolvedResultDir = (Resolve-Path -LiteralPath $ResultDir).Path
$analysisDir = Join-Path $resolvedResultDir "analysis"
Ensure-Directory -Path $analysisDir

$matrixRows = @(Import-Csv (Join-Path $resolvedResultDir "system_matrix.csv"))
$qualityRows = @(Import-Csv (Join-Path $resolvedResultDir "scenario_quality.csv"))
$capabilityRows = @(Import-Csv (Join-Path $resolvedResultDir "capability_coverage.csv"))
$summaryRows = @(Import-Csv (Join-Path $resolvedResultDir "summary.csv"))

$families = @(
    "recommendation",
    "order_query",
    "logistics_query",
    "after_sales_query",
    "knowledge_and_multimodal",
    "transactional_action"
)

$systems = @($matrixRows | Select-Object -ExpandProperty system)

$overallRows = @()
foreach ($row in $matrixRows) {
    $qualityValues = @()
    $successValues = @()
    $unsupportedValues = @()
    $latencyValues = @()

    foreach ($family in $families) {
        $quality = To-Double $row."${family}_quality_pass_rate"
        $success = To-Double $row."${family}_conversation_success_rate"
        $unsupported = To-Double $row."${family}_unsupported_rate"
        $latency = To-Double $row."${family}_p95_ms"
        $qualityValues += $quality
        $successValues += $success
        $unsupportedValues += $unsupported
        if ($unsupported -lt 1.0 -and $latency -gt 0) {
            $latencyValues += $latency
        }
    }

    $systemCapabilityRows = @($capabilityRows | Where-Object { $_.system -eq $row.system })
    $avgSupport = 0.0
    if ($systemCapabilityRows.Count -gt 0) {
        $avgSupport = ($systemCapabilityRows | ForEach-Object { To-Double $_.support_rate } | Measure-Object -Average).Average
    }

    $avgLatency = 0.0
    if ($latencyValues.Count -gt 0) {
        $avgLatency = ($latencyValues | Measure-Object -Average).Average
    }

    $overallRows += [pscustomobject]@{
        system = $row.system
        avg_quality_pass_rate = [math]::Round(($qualityValues | Measure-Object -Average).Average, 4)
        avg_conversation_success_rate = [math]::Round(($successValues | Measure-Object -Average).Average, 4)
        avg_unsupported_rate = [math]::Round(($unsupportedValues | Measure-Object -Average).Average, 4)
        avg_capability_support_rate = [math]::Round($avgSupport, 4)
        avg_supported_p95_ms = [math]::Round($avgLatency, 2)
    }
}

$overallRows = @(
    $overallRows |
        Sort-Object `
            @{ Expression = { $_.avg_quality_pass_rate }; Descending = $true }, `
            @{ Expression = { $_.avg_conversation_success_rate }; Descending = $true }, `
            @{ Expression = { $_.avg_unsupported_rate }; Descending = $false }, `
            @{ Expression = { $_.avg_supported_p95_ms }; Descending = $false }
)

$leaderRows = @()
foreach ($family in $families) {
    $best = @(
        $matrixRows |
            Sort-Object `
                @{ Expression = { To-Double $_."${family}_quality_pass_rate" }; Descending = $true }, `
                @{ Expression = { To-Double $_."${family}_conversation_success_rate" }; Descending = $true }, `
                @{ Expression = { To-Double $_."${family}_unsupported_rate" }; Descending = $false }, `
                @{ Expression = { To-Double $_."${family}_p95_ms" }; Descending = $false }
    )[0]

    $leaderRows += [pscustomobject]@{
        scenario_family = $family
        leader = $best.system
        quality_pass_rate = [math]::Round((To-Double $best."${family}_quality_pass_rate"), 4)
        conversation_success_rate = [math]::Round((To-Double $best."${family}_conversation_success_rate"), 4)
        unsupported_rate = [math]::Round((To-Double $best."${family}_unsupported_rate"), 4)
        p95_ms = [math]::Round((To-Double $best."${family}_p95_ms"), 2)
    }
}

$failureColumns = @(
    "missing_required_keywords",
    "contains_forbidden_keywords",
    "missing_required_cards",
    "missing_required_actions",
    "missing_confirmation_buttons",
    "missing_order_id",
    "hallucinated_order_id",
    "login_block_failures",
    "image_flow_failures",
    "pending_decision_failures"
)

$activeFailureColumns = @()
foreach ($column in $failureColumns) {
    $total = ($qualityRows | ForEach-Object { To-Int $_.$column } | Measure-Object -Sum).Sum
    if ($total -gt 0) {
        $activeFailureColumns += $column
    }
}

$failureRows = @()
foreach ($system in $systems) {
    $row = [ordered]@{ system = $system }
    foreach ($column in $activeFailureColumns) {
        $sum = ($qualityRows | Where-Object { $_.system -eq $system } | ForEach-Object { To-Int $_.$column } | Measure-Object -Sum).Sum
        $row[$column] = $sum
    }
    $failureRows += [pscustomobject]$row
}

$concurrencyRows = @()
foreach ($system in $systems) {
    foreach ($concurrency in @(1, 2, 4)) {
        $rows = @(
            $summaryRows |
                Where-Object {
                    $_.system -eq $system -and
                    (To-Int $_.concurrency) -eq $concurrency -and
                    (To-Int $_.eligible_conversations) -gt 0
                }
        )

        $avgP95 = 0.0
        if ($rows.Count -gt 0) {
            $avgP95 = ($rows | ForEach-Object { To-Double $_.p95_ms } | Measure-Object -Average).Average
        }

        $concurrencyRows += [pscustomobject]@{
            system = $system
            concurrency = $concurrency
            avg_p95_ms = [math]::Round($avgP95, 2)
        }
    }
}

$overallRows |
    ForEach-Object {
        $obj = [ordered]@{}
        $obj[(Get-CsvLabel "system")] = Get-SystemLabel $_.system
        $obj[(Get-CsvLabel "system_key")] = $_.system
        $obj[(Get-CsvLabel "avg_quality")] = $_.avg_quality_pass_rate
        $obj[(Get-CsvLabel "avg_success")] = $_.avg_conversation_success_rate
        $obj[(Get-CsvLabel "avg_unsupported")] = $_.avg_unsupported_rate
        $obj[(Get-CsvLabel "avg_capability")] = $_.avg_capability_support_rate
        $obj[(Get-CsvLabel "avg_supported_p95_ms")] = $_.avg_supported_p95_ms
        [pscustomobject]$obj
    } |
    Export-Csv (Join-Path $analysisDir "overall_metrics.csv") -NoTypeInformation -Encoding UTF8

$leaderRows |
    ForEach-Object {
        $obj = [ordered]@{}
        $obj[(Get-CsvLabel "scenario")] = Get-ScenarioLabel $_.scenario_family
        $obj[(Get-CsvLabel "scenario_key")] = $_.scenario_family
        $obj[(Get-CsvLabel "leader_system")] = Get-SystemLabel $_.leader
        $obj[(Get-CsvLabel "leader_system_key")] = $_.leader
        $obj[(Get-CsvLabel "quality")] = $_.quality_pass_rate
        $obj[(Get-CsvLabel "success")] = $_.conversation_success_rate
        $obj[(Get-CsvLabel "unsupported")] = $_.unsupported_rate
        $obj[(Get-CsvLabel "p95_ms")] = $_.p95_ms
        [pscustomobject]$obj
    } |
    Export-Csv (Join-Path $analysisDir "scenario_leaders.csv") -NoTypeInformation -Encoding UTF8

$failureRows |
    ForEach-Object {
        $obj = [ordered]@{}
        $obj[(Get-CsvLabel "system")] = Get-SystemLabel $_.system
        $obj[(Get-CsvLabel "system_key")] = $_.system
        foreach ($column in $activeFailureColumns) {
            $obj[(Get-FailureLabel $column)] = $_.$column
        }
        [pscustomobject]$obj
    } |
    Export-Csv (Join-Path $analysisDir "failure_breakdown.csv") -NoTypeInformation -Encoding UTF8

$concurrencyRows |
    ForEach-Object {
        $obj = [ordered]@{}
        $obj[(Get-CsvLabel "system")] = Get-SystemLabel $_.system
        $obj[(Get-CsvLabel "system_key")] = $_.system
        $obj[(Get-CsvLabel "concurrency")] = $_.concurrency
        $obj[(Get-CsvLabel "avg_p95_ms")] = $_.avg_p95_ms
        [pscustomobject]$obj
    } |
    Export-Csv (Join-Path $analysisDir "concurrency_latency.csv") -NoTypeInformation -Encoding UTF8

$qualityChartRows = @($overallRows | ForEach-Object { [pscustomobject]@{ label = (Get-SystemLabel $_.system); value = $_.avg_quality_pass_rate } })
$successChartRows = @($overallRows | ForEach-Object { [pscustomobject]@{ label = (Get-SystemLabel $_.system); value = $_.avg_conversation_success_rate } })
$unsupportedChartRows = @($overallRows | ForEach-Object { [pscustomobject]@{ label = (Get-SystemLabel $_.system); value = $_.avg_unsupported_rate } })
$latencyChartRows = @($overallRows | Sort-Object avg_supported_p95_ms -Descending | ForEach-Object { [pscustomobject]@{ label = (Get-SystemLabel $_.system); value = $_.avg_supported_p95_ms } })

Write-SvgBarChart -Path (Join-Path $analysisDir "overall_quality_pass_rate.svg") `
    -Title $script:Texts.charts.overall_quality_title `
    -Subtitle $script:Texts.charts.overall_quality_subtitle `
    -Rows $qualityChartRows `
    -BaseColor "#2563EB"

Write-SvgBarChart -Path (Join-Path $analysisDir "overall_conversation_success_rate.svg") `
    -Title $script:Texts.charts.overall_success_title `
    -Subtitle $script:Texts.charts.overall_success_subtitle `
    -Rows $successChartRows `
    -BaseColor "#059669"

Write-SvgBarChart -Path (Join-Path $analysisDir "overall_unsupported_rate.svg") `
    -Title $script:Texts.charts.overall_unsupported_title `
    -Subtitle $script:Texts.charts.overall_unsupported_subtitle `
    -Rows $unsupportedChartRows `
    -Gradient

Write-SvgBarChart -Path (Join-Path $analysisDir "supported_latency_p95_ms.svg") `
    -Title $script:Texts.charts.supported_p95_title `
    -Subtitle $script:Texts.charts.supported_p95_subtitle `
    -Rows $latencyChartRows `
    -BaseColor "#7C3AED"

$qualityHeatmapValues = @()
foreach ($system in $systems) {
    $matrixRow = @($matrixRows | Where-Object { $_.system -eq $system })[0]
    $qualityHeatmapValues += ,@($families | ForEach-Object { To-Double $matrixRow."${_}_quality_pass_rate" })
}

Write-SvgHeatmap -Path (Join-Path $analysisDir "scenario_quality_heatmap.svg") `
    -Title $script:Texts.charts.scenario_quality_title `
    -Subtitle $script:Texts.charts.scenario_quality_subtitle `
    -RowLabels ($systems | ForEach-Object { Get-SystemLabel $_ }) `
    -ColumnLabels ($families | ForEach-Object { Get-ScenarioLabel $_ }) `
    -Values $qualityHeatmapValues `
    -MinValue 0 `
    -MaxValue 1 `
    -StartRgb @(239, 246, 255) `
    -EndRgb @(29, 78, 216)

if ($activeFailureColumns.Count -gt 0) {
    $failureHeatmapValues = @()
    foreach ($system in $systems) {
        $failureRow = @($failureRows | Where-Object { $_.system -eq $system })[0]
        $failureHeatmapValues += ,@($activeFailureColumns | ForEach-Object { To-Double $failureRow.$_ })
    }
    $maxFailure = ($failureHeatmapValues | ForEach-Object { $_ } | Measure-Object -Maximum).Maximum
    Write-SvgHeatmap -Path (Join-Path $analysisDir "failure_breakdown_heatmap.svg") `
        -Title $script:Texts.charts.failure_title `
        -Subtitle $script:Texts.charts.failure_subtitle `
        -RowLabels ($systems | ForEach-Object { Get-SystemLabel $_ }) `
        -ColumnLabels ($activeFailureColumns | ForEach-Object { Get-FailureLabel $_ }) `
        -Values $failureHeatmapValues `
        -MinValue 0 `
        -MaxValue ([math]::Max(1, $maxFailure)) `
        -StartRgb @(255, 245, 245) `
        -EndRgb @(185, 28, 28)
}

$concurrencyHeatmapValues = @()
foreach ($system in $systems) {
    $rowValues = @()
    foreach ($c in @(1, 2, 4)) {
        $match = @($concurrencyRows | Where-Object { $_.system -eq $system -and $_.concurrency -eq $c })[0]
        $rowValues += $match.avg_p95_ms
    }
    $concurrencyHeatmapValues += ,$rowValues
}

$maxConcurrency = ($concurrencyHeatmapValues | ForEach-Object { $_ } | Measure-Object -Maximum).Maximum
Write-SvgHeatmap -Path (Join-Path $analysisDir "concurrency_latency_heatmap.svg") `
    -Title $script:Texts.charts.concurrency_title `
    -Subtitle $script:Texts.charts.concurrency_subtitle `
    -RowLabels ($systems | ForEach-Object { Get-SystemLabel $_ }) `
    -ColumnLabels @($script:Texts.charts.concurrency_labels) `
    -Values $concurrencyHeatmapValues `
    -MinValue 0 `
    -MaxValue ([math]::Max(1, $maxConcurrency)) `
    -StartRgb @(245, 243, 255) `
    -EndRgb @(91, 33, 182)

$bestFullCapability = @(
    $overallRows |
        Where-Object { $_.avg_capability_support_rate -ge 0.99 } |
        Sort-Object `
            @{ Expression = { $_.avg_quality_pass_rate }; Descending = $true }, `
            @{ Expression = { $_.avg_conversation_success_rate }; Descending = $true }, `
            @{ Expression = { $_.avg_supported_p95_ms }; Descending = $false }
)[0]

$baseMixed = @($overallRows | Where-Object { $_.system -eq "rasa_plus_llm_base" })[0]
$loraMixed = @($overallRows | Where-Object { $_.system -eq "rasa_plus_llm_lora" })[0]
$unsupportedHeavy = @($overallRows | Where-Object { $_.avg_unsupported_rate -ge 0.6 } | Select-Object -ExpandProperty system)

$priorityRows = @(
    $qualityRows |
        Where-Object { $_.system -in @("rasa_plus_llm_base", "rasa_plus_llm_lora", "rasa_only") } |
        ForEach-Object {
            [pscustomobject]@{
                system = $_.system
                scenario_family = $_.scenario_family
                missing_total = (
                    (To-Int $_.missing_required_keywords) +
                    (To-Int $_.missing_required_cards) +
                    (To-Int $_.missing_required_actions) +
                    (To-Int $_.missing_confirmation_buttons) +
                    (To-Int $_.missing_order_id) +
                    (To-Int $_.hallucinated_order_id) +
                    (To-Int $_.login_block_failures)
                )
            }
        } |
        Sort-Object missing_total -Descending
)

$reportLines = New-Object System.Collections.Generic.List[string]
$reportLines.Add([string]("# " + $script:Texts.report.title))
$reportLines.Add("")
$reportLines.Add([string]("## " + $script:Texts.report.overall_heading))
$reportLines.Add("")
$reportLines.Add([string]$script:Texts.report.overall_intro)
foreach ($line in @($script:Texts.report.overall_notes)) {
    $reportLines.Add("- $line")
}
$reportLines.Add("")

$overallTableRows = @()
foreach ($row in $overallRows) {
    $overallTableRows += ,@(
        (Get-SystemLabel $row.system),
        $row.system,
        $row.avg_quality_pass_rate,
        $row.avg_conversation_success_rate,
        $row.avg_unsupported_rate,
        $row.avg_capability_support_rate,
        $row.avg_supported_p95_ms
    )
}
foreach ($line in (New-MarkdownTable -Headers @($script:Texts.report.overall_headers) -Rows $overallTableRows)) {
    $reportLines.Add($line)
}

$reportLines.Add("")
$reportLines.Add([string]("## " + $script:Texts.report.figures_heading))
$reportLines.Add("")
$reportLines.Add([string]$script:Texts.report.figures_intro)
$reportLines.Add("")
$reportLines.Add(("![{0}](analysis/overall_quality_pass_rate.svg)" -f $script:Texts.charts.overall_quality_title))
$reportLines.Add("")
$reportLines.Add(("![{0}](analysis/overall_conversation_success_rate.svg)" -f $script:Texts.charts.overall_success_title))
$reportLines.Add("")
$reportLines.Add(("![{0}](analysis/overall_unsupported_rate.svg)" -f $script:Texts.charts.overall_unsupported_title))
$reportLines.Add("")
$reportLines.Add(("![{0}](analysis/supported_latency_p95_ms.svg)" -f $script:Texts.charts.supported_p95_title))
$reportLines.Add("")
$reportLines.Add(("![{0}](analysis/scenario_quality_heatmap.svg)" -f $script:Texts.charts.scenario_quality_title))
$reportLines.Add("")
if ($activeFailureColumns.Count -gt 0) {
    $reportLines.Add(("![{0}](analysis/failure_breakdown_heatmap.svg)" -f $script:Texts.charts.failure_title))
    $reportLines.Add("")
}
$reportLines.Add(("![{0}](analysis/concurrency_latency_heatmap.svg)" -f $script:Texts.charts.concurrency_title))
$reportLines.Add("")
$reportLines.Add([string]("## " + $script:Texts.report.scenario_heading))
$reportLines.Add("")
$reportLines.Add([string]$script:Texts.report.scenario_intro)
$reportLines.Add("")

$leaderTableRows = @()
foreach ($row in $leaderRows) {
    $leaderTableRows += ,@(
        (Get-ScenarioLabel $row.scenario_family),
        $row.scenario_family,
        (Get-SystemLabel $row.leader),
        $row.leader,
        $row.quality_pass_rate,
        $row.conversation_success_rate,
        $row.unsupported_rate,
        $row.p95_ms
    )
}
foreach ($line in (New-MarkdownTable -Headers @($script:Texts.report.scenario_headers) -Rows $leaderTableRows)) {
    $reportLines.Add($line)
}

$reportLines.Add("")
$reportLines.Add([string]("## " + $script:Texts.report.conclusion_heading))
$reportLines.Add("")
$reportLines.Add(("1. " + ($script:Texts.report.conclusion_best_1 -f $bestFullCapability.system)))
$reportLines.Add("   " + ($script:Texts.report.conclusion_best_2 -f $bestFullCapability.system, (Get-SystemLabel $bestFullCapability.system), $bestFullCapability.avg_quality_pass_rate, $bestFullCapability.avg_conversation_success_rate, $bestFullCapability.avg_supported_p95_ms))
$reportLines.Add(("2. " + $script:Texts.report.conclusion_lora_1))
$reportLines.Add("   " + ($script:Texts.report.conclusion_lora_2 -f $baseMixed.avg_supported_p95_ms, $loraMixed.avg_supported_p95_ms))
$reportLines.Add(("3. " + $script:Texts.report.conclusion_bottleneck_1))
$reportLines.Add("   " + $script:Texts.report.conclusion_bottleneck_2)
if ($unsupportedHeavy.Count -gt 0) {
    $joinedUnsupported = [string]::Join(([string][char]0x3001), $unsupportedHeavy)
    $reportLines.Add(("4. " + ($script:Texts.report.conclusion_unsupported_1 -f $joinedUnsupported)))
    $reportLines.Add("   " + $script:Texts.report.conclusion_unsupported_2)
}
$reportLines.Add(("5. " + $script:Texts.report.conclusion_llm_1))
$reportLines.Add("   " + $script:Texts.report.conclusion_llm_2)
$reportLines.Add("")
$reportLines.Add([string]("## " + $script:Texts.report.priority_heading))
$reportLines.Add("")
foreach ($line in @($script:Texts.report.priority_items)) {
    $reportLines.Add("- $line")
}
$reportLines.Add("")
$reportLines.Add([string]("## " + $script:Texts.report.risk_heading))
$reportLines.Add("")
$reportLines.Add([string]$script:Texts.report.risk_intro)
$reportLines.Add("")

$riskTableRows = @()
foreach ($row in ($priorityRows | Select-Object -First 8)) {
    $riskTableRows += ,@(
        (Get-SystemLabel $row.system),
        $row.system,
        (Get-ScenarioLabel $row.scenario_family),
        $row.scenario_family,
        $row.missing_total
    )
}
foreach ($line in (New-MarkdownTable -Headers @($script:Texts.report.risk_headers) -Rows $riskTableRows)) {
    $reportLines.Add($line)
}

$reportLines.Add("")
$reportLines.Add([string]("## " + $script:Texts.report.notes_heading))
$reportLines.Add("")
foreach ($line in @($script:Texts.report.notes)) {
    $reportLines.Add("- $line")
}

Set-Content -LiteralPath (Join-Path $resolvedResultDir "detailed_analysis.md") -Value $reportLines -Encoding UTF8
Write-Host "analysis written to: $resolvedResultDir"
