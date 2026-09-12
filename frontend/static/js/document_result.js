const pathParts = window.location.pathname.split("/");

const documentName = decodeURIComponent(
    pathParts[pathParts.length - 1]
);


function displayValue(value) {
    if (value === null || value === undefined) {
        return "N/A";
    }

    if (typeof value === "object") {
        return JSON.stringify(value);
    }

    return String(value);
}


function displayConfidence(value) {
    if (value === null || value === undefined) {
        return "N/A";
    }

    return `${value}%`;
}


function createFieldTable(data) {

    if (
        !data ||
        typeof data !== "object"
    ) {
        return null;
    }

    const table =
        document.createElement("table");

    table.className = "result-table";

    table.innerHTML = `
        <thead>
            <tr>
                <th>Field</th>
                <th>Value</th>
                <th>Confidence</th>
                <th>Evidence</th>
                <th>Page</th>
            </tr>
        </thead>
        <tbody></tbody>
    `;

    const tbody =
        table.querySelector("tbody");

    Object.entries(data).forEach(
        ([fieldName, fieldValue]) => {

            if (
                Array.isArray(fieldValue)
            ) {
                return;
            }

            if (
                fieldName === "document_type"
            ) {
                return;
            }

            const row =
                document.createElement("tr");

            let value = fieldValue;
            let confidence = null;
            let sourceText = null;
            let pageNumber = null;

            if (
                fieldValue &&
                typeof fieldValue === "object"
            ) {
                value =
                    fieldValue.value;

                confidence =
                    fieldValue.confidence;

                sourceText =
                    fieldValue.source_text;

                pageNumber =
                    fieldValue.page_number;
            }

            const fieldCell =
                document.createElement("td");

            fieldCell.textContent =
                fieldName;

            const valueCell =
                document.createElement("td");

            valueCell.textContent =
                displayValue(value);

            const confidenceCell =
                document.createElement("td");

            confidenceCell.textContent =
                displayConfidence(confidence);

            const evidenceCell =
                document.createElement("td");

            evidenceCell.textContent =
                displayValue(sourceText);

            const pageCell =
                document.createElement("td");

            pageCell.textContent =
                displayValue(pageNumber);

            row.appendChild(fieldCell);
            row.appendChild(valueCell);
            row.appendChild(confidenceCell);
            row.appendChild(evidenceCell);
            row.appendChild(pageCell);

            tbody.appendChild(row);
        }
    );

    return table;
}


function createDynamicTable(items) {

    if (
        !Array.isArray(items) ||
        items.length === 0
    ) {
        return null;
    }

    const table =
        document.createElement("table");

    table.className = "result-table";

    const keys =
        new Set();

    items.forEach((item) => {

        if (
            item &&
            typeof item === "object"
        ) {
            Object.keys(item).forEach(
                (key) => keys.add(key)
            );
        }
    });

    const columns =
        Array.from(keys);

    const header =
        document.createElement("thead");

    const headerRow =
        document.createElement("tr");

    columns.forEach((column) => {

        const cell =
            document.createElement("th");

        cell.textContent =
            column;

        headerRow.appendChild(cell);
    });

    header.appendChild(headerRow);

    table.appendChild(header);

    const tbody =
        document.createElement("tbody");

    items.forEach((item) => {

        const row =
            document.createElement("tr");

        columns.forEach((column) => {

            const cell =
                document.createElement("td");

            const value =
                item[column];

            if (
                value &&
                typeof value === "object" &&
                !Array.isArray(value)
            ) {
                cell.textContent =
                    JSON.stringify(value);
            } else {
                cell.textContent =
                    displayValue(value);
            }

            row.appendChild(cell);
        });

        tbody.appendChild(row);
    });

    table.appendChild(tbody);

    return table;
}


function createFinancialLineItemTable(items) {

    if (
        !Array.isArray(items) ||
        items.length === 0
    ) {
        return null;
    }

    const rows =
        items.map((item) => {

            if (
                !item ||
                typeof item !== "object"
            ) {
                return item;
            }

            const values =
                item.values || {};

            return {
                ...values,
                page_number:
                    item.page_number
            };
        });

    return createDynamicTable(rows);
}


function displayExtractedData(data) {

    const container =
        document.getElementById(
            "extractedData"
        );

    container.innerHTML = "";

    if (!data) {

        container.textContent =
            "No extracted data.";

        return;
    }


    const documentType =
        document.createElement("p");

    documentType.innerHTML =
        "<strong>Document Type:</strong>";

    const documentTypeValue =
        document.createTextNode(
            ` ${displayValue(data.document_type)}`
        );

    documentType.appendChild(
        documentTypeValue
    );

    container.appendChild(
        documentType
    );


    const fieldsTable =
        createFieldTable(data);

    if (fieldsTable) {

        const heading =
            document.createElement("h3");

        heading.textContent =
            "Extracted Fields";

        container.appendChild(
            heading
        );

        container.appendChild(
            fieldsTable
        );
    }


    Object.entries(data).forEach(
        ([fieldName, fieldValue]) => {

            if (
                !Array.isArray(fieldValue)
            ) {
                return;
            }

            const heading =
                document.createElement("h3");

            heading.textContent =
                fieldName;

            container.appendChild(
                heading
            );

            let table = null;

            if (
                fieldName === "line_items"
            ) {
                table =
                    createFinancialLineItemTable(
                        fieldValue
                    );
            } else {
                table =
                    createDynamicTable(
                        fieldValue
                    );
            }

            if (table) {
                container.appendChild(
                    table
                );
            }
        }
    );
}


function displayValidation(validation) {

    const tbody =
        document.getElementById(
            "validationTableBody"
        );

    tbody.innerHTML = "";

    if (!validation) {
        return;
    }


    document.getElementById(
        "validationStatus"
    ).textContent =
        displayValue(
            validation.overall_status
        );


    const issues =
        document.getElementById(
            "validationIssues"
        );

    issues.innerHTML = "";


    if (
        !validation.issues ||
        validation.issues.length === 0
    ) {

        const li =
            document.createElement("li");

        li.textContent =
            "No issues.";

        issues.appendChild(li);

    } else {

        validation.issues.forEach(
            (issue) => {

                const li =
                    document.createElement("li");

                li.textContent =
                    issue;

                issues.appendChild(li);
            }
        );
    }


    (validation.checks || []).forEach(
        (check) => {

            const row =
                document.createElement("tr");

            const values = [
                check.name,
                check.formula,
                check.calculated_value,
                check.reported_value,
                check.variance,
                check.status
            ];

            values.forEach((value) => {

                const cell =
                    document.createElement("td");

                cell.textContent =
                    displayValue(value);

                row.appendChild(cell);
            });

            tbody.appendChild(row);
        }
    );
}


async function loadDocument() {

    try {

        const response =
            await fetch(
                `/api/v1/documents/${encodeURIComponent(documentName)}`
            );


        const contentType =
            response.headers.get(
                "content-type"
            ) || "";


        let result;


        if (
            contentType.includes(
                "application/json"
            )
        ) {

            result =
                await response.json();

        } else {

            result = {
                detail: {
                    message:
                        await response.text()
                }
            };
        }


        if (!response.ok) {

            throw new Error(
                result.detail?.message ||
                "Failed to load document."
            );
        }


        document.getElementById(
            "documentName"
        ).textContent =
            displayValue(
                result.document_name
            );


        document.getElementById(
            "documentType"
        ).textContent =
            displayValue(
                result.document_type
            );


        document.getElementById(
            "processingStatus"
        ).textContent =
            displayValue(
                result.processing_status
            );


        const confidence =
            result.overall_confidence;


        document.getElementById(
            "overallConfidence"
        ).textContent =
            confidence === null ||
            confidence === undefined
                ? "N/A"
                : `${(
                    confidence * 100
                ).toFixed(2)}%`;


        const fileValidation =
            result.file_validation;


        document.getElementById(
            "fileType"
        ).textContent =
            displayValue(
                fileValidation?.file_type
            );


        document.getElementById(
            "isSupported"
        ).textContent =
            displayValue(
                fileValidation?.is_supported
            );


        document.getElementById(
            "isReadable"
        ).textContent =
            displayValue(
                fileValidation?.is_readable
            );


        document.getElementById(
            "pageCount"
        ).textContent =
            displayValue(
                fileValidation?.page_count
            );


        document.getElementById(
            "fileStatus"
        ).textContent =
            displayValue(
                fileValidation?.status
            );


        displayExtractedData(
            result.extracted_data
        );


        displayValidation(
            result.validation
        );


        const metadata =
            result.processing_metadata;


        document.getElementById(
            "ocrUsed"
        ).textContent =
            displayValue(
                metadata?.ocr_used
            );


        document.getElementById(
            "processedAt"
        ).textContent =
            displayValue(
                metadata?.processed_at
            );


        document.getElementById(
            "processingTime"
        ).textContent =
            displayValue(
                metadata?.processing_time_ms
            ) + " ms";


        document.getElementById(
            "rawJson"
        ).textContent =
            JSON.stringify(
                result,
                null,
                2
            );

    } catch (error) {

        console.error(error);

        const errorMessage =
            document.createElement("p");

        errorMessage.textContent =
            error.message;

        document.body.appendChild(
            errorMessage
        );
    }
}


loadDocument();