import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";
const payloadPath = process.argv[2];
const outputPath = process.argv[3];
const qaDirectory = process.argv[4];
if (!payloadPath || !outputPath || !qaDirectory) {
  throw new Error("usage: node build_analysis_workbook.mjs payload.json output.xlsx qa_directory");
}
const payload = JSON.parse(await fs.readFile(payloadPath, "utf8"));
const workbook = Workbook.create();
const sourceSheet = workbook.worksheets.add("Source Results");
const stackingSheet = workbook.worksheets.add("Stacking Results");
const runSheet = workbook.worksheets.add("Run Information");
writeTableSheet(sourceSheet, payload.source_columns, payload.source_rows, "SourceResultsTable");
writeTableSheet(stackingSheet, payload.stacking_columns, payload.stacking_rows, "StackingResultsTable");
writeRunSheet(runSheet, payload.run_information);
await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.mkdir(qaDirectory, { recursive: true });
for (const sheetName of ["Source Results", "Stacking Results", "Run Information"]) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const used = sheet.getUsedRange(true);
  const rowCount = Math.min(used.rowCount, 25);
  const colCount = Math.min(used.columnCount, 16);
  const previewRange = sheet.getRangeByIndexes(0, 0, rowCount, colCount);
  const preview = await workbook.render({ sheetName, range: previewRange.address, scale: 1.5, format: "png" });
  await fs.writeFile(path.join(qaDirectory, `${sheetName.toLowerCase().replaceAll(" ", "_")}.png`), new Uint8Array(await preview.arrayBuffer()));
}
const sourceCheck = await workbook.inspect({ kind: "table", range: "'Source Results'!A1:P25", include: "values,formulas", tableMaxRows: 25, tableMaxCols: 16 });
const stackingCheck = await workbook.inspect({ kind: "table", range: "'Stacking Results'!A1:L25", include: "values,formulas", tableMaxRows: 25, tableMaxCols: 12 });
const runCheck = await workbook.inspect({ kind: "table", range: "'Run Information'!A1:B25", include: "values,formulas", tableMaxRows: 25, tableMaxCols: 2 });
await fs.writeFile(path.join(qaDirectory, "key_ranges.ndjson"), `${sourceCheck.ndjson}\n${stackingCheck.ndjson}\n${runCheck.ndjson}\n`);
const errorScan = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan" });
if (errorScan.ndjson.includes("#REF!") || errorScan.ndjson.includes("#DIV/0!") || errorScan.ndjson.includes("#VALUE!") || errorScan.ndjson.includes("#NAME?") || errorScan.ndjson.includes("#N/A")) {
  throw new Error(`workbook formula error scan failed: ${errorScan.ndjson}`);
}
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
function writeTableSheet(sheet, columns, rows, tableName) {
  sheet.showGridLines = false;
  const values = [columns, ...rows];
  const range = sheet.getRangeByIndexes(0, 0, values.length, columns.length);
  range.values = values;
  range.format.font = { name: "Aptos", size: 10, color: "#17212B" };
  const header = sheet.getRangeByIndexes(0, 0, 1, columns.length);
  header.format.fill = "#244B5A";
  header.format.font = { name: "Aptos", size: 10, bold: true, color: "#FFFFFF" };
  header.format.wrapText = true;
  header.format.rowHeightPx = 48;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(Math.min(2, columns.length));
  if (rows.length > 0) {
    const table = sheet.tables.add(range.address, true, tableName);
    table.style = "TableStyleMedium2";
    table.showBandedColumns = false;
    table.showFilterButton = true;
  }
  for (let col = 0; col < columns.length; col += 1) {
    const name = String(columns[col]);
    const columnRange = sheet.getRangeByIndexes(0, col, values.length, 1);
    columnRange.format.columnWidthPx = columnWidth(name);
    if (name.includes("fraction")) {
      columnRange.format.numberFormat = "0.00%";
    } else if (isProbabilityColumn(name) || name.includes("flux")) {
      columnRange.format.numberFormat = "0.000E+00";
    } else if (isIntegerColumn(name)) {
      columnRange.format.numberFormat = "#,##0";
    } else if (isNumericColumn(name)) {
      columnRange.format.numberFormat = "0.0000";
    }
  }
  const significanceIndex = columns.indexOf("pre_trial_significance");
  if (significanceIndex >= 0 && rows.length > 0) {
    const significanceRange = sheet.getRangeByIndexes(1, significanceIndex, rows.length, 1);
    significanceRange.conditionalFormats.add("colorScale", { thresholds: ["min", "50%", "max"], colors: ["#FFFFFF", "#F6D55C", "#C43C39"] });
  }
}
function writeRunSheet(sheet, rows) {
  sheet.showGridLines = false;
  const range = sheet.getRangeByIndexes(0, 0, rows.length, 2);
  range.values = rows;
  range.format.font = { name: "Aptos", size: 10, color: "#17212B" };
  const header = sheet.getRange("A1:B1");
  header.format.fill = "#244B5A";
  header.format.font = { name: "Aptos", size: 10, bold: true, color: "#FFFFFF" };
  sheet.getRange("A:A").format.columnWidthPx = 230;
  sheet.getRange("B:B").format.columnWidthPx = 520;
  sheet.getRange("B:B").format.wrapText = true;
  sheet.freezePanes.freezeRows(1);
  const table = sheet.tables.add(range.address, true, "RunInformationTable");
  table.style = "TableStyleMedium2";
}
function columnWidth(name) {
  if (name.includes("name") || name.includes("status")) return 170;
  if (name.includes("p") || name.includes("significance") || name.includes("flux")) return 135;
  if (name.includes("ra_") || name.includes("dec_") || name.includes("weight")) return 115;
  return Math.min(Math.max(95, name.length * 8 + 24), 220);
}
function isProbabilityColumn(name) {
  return name.endsWith("_p");
}
function isIntegerColumn(name) {
  return name === "source_number" || name === "significance_rank" || name === "n_sources" || name === "n_events_in_roi";
}
function isNumericColumn(name) {
  return name.includes("ns") || name === "ts" || name.includes("significance") || name.includes("weight") || name.endsWith("_deg") || name === "spectral_index";
}