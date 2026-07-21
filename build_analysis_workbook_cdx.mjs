import fs from "node:fs/promises"; // Codex
import path from "node:path"; // Codex
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool"; // Codex


const payloadPath = process.argv[2]; // Codex
const outputPath = process.argv[3]; // Codex
const qaDirectory = process.argv[4]; // Codex
if (!payloadPath || !outputPath || !qaDirectory) { // Codex
  throw new Error("usage: node build_analysis_workbook_cdx.mjs payload.json output.xlsx qa_directory"); // Codex
} // Codex
const payload = JSON.parse(await fs.readFile(payloadPath, "utf8")); // Codex
const workbook = Workbook.create(); // Codex
const sourceSheet = workbook.worksheets.add("Source Results"); // Codex
const stackingSheet = workbook.worksheets.add("Stacking Results"); // Codex
const runSheet = workbook.worksheets.add("Run Information"); // Codex
writeTableSheet(sourceSheet, payload.source_columns, payload.source_rows, "SourceResultsTable"); // Codex
writeTableSheet(stackingSheet, payload.stacking_columns, payload.stacking_rows, "StackingResultsTable"); // Codex
writeRunSheet(runSheet, payload.run_information); // Codex
await fs.mkdir(path.dirname(outputPath), { recursive: true }); // Codex
await fs.mkdir(qaDirectory, { recursive: true }); // Codex
for (const sheetName of ["Source Results", "Stacking Results", "Run Information"]) { // Codex
  const sheet = workbook.worksheets.getItem(sheetName); // Codex
  const used = sheet.getUsedRange(true); // Codex
  const rowCount = Math.min(used.rowCount, 25); // Codex
  const colCount = Math.min(used.columnCount, 16); // Codex
  const previewRange = sheet.getRangeByIndexes(0, 0, rowCount, colCount); // Codex
  const preview = await workbook.render({ sheetName, range: previewRange.address, scale: 1.5, format: "png" }); // Codex
  await fs.writeFile(path.join(qaDirectory, `${sheetName.toLowerCase().replaceAll(" ", "_")}.png`), new Uint8Array(await preview.arrayBuffer())); // Codex
} // Codex
const sourceCheck = await workbook.inspect({ kind: "table", range: "'Source Results'!A1:P25", include: "values,formulas", tableMaxRows: 25, tableMaxCols: 16 }); // Codex
const stackingCheck = await workbook.inspect({ kind: "table", range: "'Stacking Results'!A1:L25", include: "values,formulas", tableMaxRows: 25, tableMaxCols: 12 }); // Codex
const runCheck = await workbook.inspect({ kind: "table", range: "'Run Information'!A1:B25", include: "values,formulas", tableMaxRows: 25, tableMaxCols: 2 }); // Codex
await fs.writeFile(path.join(qaDirectory, "key_ranges.ndjson"), `${sourceCheck.ndjson}\n${stackingCheck.ndjson}\n${runCheck.ndjson}\n`); // Codex
const errorScan = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan" }); // Codex
if (errorScan.ndjson.includes("#REF!") || errorScan.ndjson.includes("#DIV/0!") || errorScan.ndjson.includes("#VALUE!") || errorScan.ndjson.includes("#NAME?") || errorScan.ndjson.includes("#N/A")) { // Codex
  throw new Error(`workbook formula error scan failed: ${errorScan.ndjson}`); // Codex
} // Codex
const output = await SpreadsheetFile.exportXlsx(workbook); // Codex
await output.save(outputPath); // Codex


function writeTableSheet(sheet, columns, rows, tableName) { // Codex
  sheet.showGridLines = false; // Codex
  const values = [columns, ...rows]; // Codex
  const range = sheet.getRangeByIndexes(0, 0, values.length, columns.length); // Codex
  range.values = values; // Codex
  range.format.font = { name: "Aptos", size: 10, color: "#17212B" }; // Codex
  const header = sheet.getRangeByIndexes(0, 0, 1, columns.length); // Codex
  header.format.fill = "#244B5A"; // Codex
  header.format.font = { name: "Aptos", size: 10, bold: true, color: "#FFFFFF" }; // Codex
  header.format.wrapText = true; // Codex
  header.format.rowHeightPx = 48; // Codex
  sheet.freezePanes.freezeRows(1); // Codex
  sheet.freezePanes.freezeColumns(Math.min(2, columns.length)); // Codex
  if (rows.length > 0) { // Codex
    const table = sheet.tables.add(range.address, true, tableName); // Codex
    table.style = "TableStyleMedium2"; // Codex
    table.showBandedColumns = false; // Codex
    table.showFilterButton = true; // Codex
  } // Codex
  for (let col = 0; col < columns.length; col += 1) { // Codex
    const name = String(columns[col]); // Codex
    const columnRange = sheet.getRangeByIndexes(0, col, values.length, 1); // Codex
    columnRange.format.columnWidthPx = columnWidth(name); // Codex
    if (name.includes("fraction")) { // Codex
      columnRange.format.numberFormat = "0.00%"; // Codex
    } else if (isProbabilityColumn(name) || name.includes("flux")) { // Codex
      columnRange.format.numberFormat = "0.000E+00"; // Codex
    } else if (isIntegerColumn(name)) { // Codex
      columnRange.format.numberFormat = "#,##0"; // Codex
    } else if (isNumericColumn(name)) { // Codex
      columnRange.format.numberFormat = "0.0000"; // Codex
    } // Codex
  } // Codex
  const significanceIndex = columns.indexOf("pre_trial_significance"); // Codex
  if (significanceIndex >= 0 && rows.length > 0) { // Codex
    const significanceRange = sheet.getRangeByIndexes(1, significanceIndex, rows.length, 1); // Codex
    significanceRange.conditionalFormats.add("colorScale", { thresholds: ["min", "50%", "max"], colors: ["#FFFFFF", "#F6D55C", "#C43C39"] }); // Codex
  } // Codex
} // Codex


function writeRunSheet(sheet, rows) { // Codex
  sheet.showGridLines = false; // Codex
  const range = sheet.getRangeByIndexes(0, 0, rows.length, 2); // Codex
  range.values = rows; // Codex
  range.format.font = { name: "Aptos", size: 10, color: "#17212B" }; // Codex
  const header = sheet.getRange("A1:B1"); // Codex
  header.format.fill = "#244B5A"; // Codex
  header.format.font = { name: "Aptos", size: 10, bold: true, color: "#FFFFFF" }; // Codex
  sheet.getRange("A:A").format.columnWidthPx = 230; // Codex
  sheet.getRange("B:B").format.columnWidthPx = 520; // Codex
  sheet.getRange("B:B").format.wrapText = true; // Codex
  sheet.freezePanes.freezeRows(1); // Codex
  const table = sheet.tables.add(range.address, true, "RunInformationTable"); // Codex
  table.style = "TableStyleMedium2"; // Codex
} // Codex


function columnWidth(name) { // Codex
  if (name.includes("name") || name.includes("status")) return 170; // Codex
  if (name.includes("p") || name.includes("significance") || name.includes("flux")) return 135; // Codex
  if (name.includes("ra_") || name.includes("dec_") || name.includes("weight")) return 115; // Codex
  return Math.min(Math.max(95, name.length * 8 + 24), 220); // Codex
} // Codex


function isProbabilityColumn(name) { // Codex
  return name.endsWith("_p"); // Codex
} // Codex


function isIntegerColumn(name) { // Codex
  return name === "source_number" || name === "significance_rank" || name === "n_sources" || name === "n_events_in_roi"; // Codex
} // Codex


function isNumericColumn(name) { // Codex
  return name.includes("ns") || name === "ts" || name.includes("significance") || name.includes("weight") || name.includes("flux") || name.includes("fraction") || name.endsWith("_deg") || name === "spectral_index"; // Codex
} // Codex
