const documentForm = document.getElementById("documentForm");
const documentType = document.getElementById("documentType");
const documentFile = document.getElementById("documentFile");
const message = document.getElementById("message");
const processButton = document.getElementById("processButton");

const processingPanel = document.getElementById(
    "processingPanel"
);

const documentsTableBody = document.getElementById(
    "documentsTableBody"
);

const refreshDocuments = document.getElementById(
    "refreshDocuments"
);


function setStep(stepId, status) {
    const step = document.getElementById(stepId);

    if (!step) {
        return;
    }

    const icon = step.querySelector(".step-icon");

    step.classList.remove(
        "step-active",
        "step-complete",
        "step-failed"
    );

    if (status === "active") {
        step.classList.add("step-active");
        icon.textContent = "●";
    }

    if (status === "complete") {
        step.classList.add("step-complete");
        icon.textContent = "✓";
    }

    if (status === "failed") {
        step.classList.add("step-failed");
        icon.textContent = "✕";
    }
}


function resetProcessingSteps() {
    const steps = [
        "stepUpload",
        "stepValidation",
        "stepExtraction",
        "stepAI",
        "stepFinancial",
        "stepStorage",
        "stepComplete"
    ];

    steps.forEach((stepId) => {
        setStep(stepId, "reset");
    });
}


function startProcessingSteps() {
    processingPanel.classList.remove("hidden");

    resetProcessingSteps();

    setStep(
        "stepUpload",
        "complete"
    );

    setStep(
        "stepValidation",
        "active"
    );
}


function updateProcessingSteps(result) {
    const validation =
        result.file_validation;

    if (
        validation &&
        validation.status === "PASS"
    ) {
        setStep(
            "stepValidation",
            "complete"
        );
    } else {
        setStep(
            "stepValidation",
            "failed"
        );

        return;
    }

    setStep(
        "stepExtraction",
        "complete"
    );

    setStep(
        "stepAI",
        "complete"
    );

    if (result.validation) {
        setStep(
            "stepFinancial",
            "complete"
        );
    }

    setStep(
        "stepStorage",
        "complete"
    );

    setStep(
        "stepComplete",
        "complete"
    );
}


async function loadDocuments() {
    try {
        const response = await fetch(
            "/api/v1/documents/"
        );

        if (!response.ok) {
            throw new Error(
                "Failed to load documents."
            );
        }

        const documents =
            await response.json();

        documentsTableBody.innerHTML = "";

        documents.forEach((documentItem) => {

            const row =
                document.createElement("tr");

            row.innerHTML = `
                <td>
                    <a href="/documents/${encodeURIComponent(documentItem.document_name)}">
                        ${documentItem.document_name}
                    </a>
                </td>

                <td>
                    ${documentItem.document_type}
                </td>

                <td>
                    ${documentItem.processing_status}
                </td>

                <td>
                    ${documentItem.created_at}
                </td>
            `;

            documentsTableBody.appendChild(row);
        });

    } catch (error) {

        message.textContent =
            error.message;
    }
}


documentForm.addEventListener(
    "submit",
    async (event) => {

        event.preventDefault();

        const file =
            documentFile.files[0];

        if (!file) {

            message.textContent =
                "Please select a document.";

            return;
        }

        if (!documentType.value) {

            message.textContent =
                "Please select a document type.";

            return;
        }

        const formData =
            new FormData();

        formData.append(
            "file",
            file
        );

        formData.append(
            "document_type",
            documentType.value
        );

        processButton.disabled = true;

        message.textContent =
            "Processing document...";

        startProcessingSteps();

        try {

            const response =
                await fetch(
                    "/api/v1/documents/process",
                    {
                        method: "POST",
                        body: formData
                    }
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

                const errorCode =
                    result.detail?.code;

                if (
                    errorCode ===
                        "UNSUPPORTED_FILE_TYPE" ||
                    errorCode ===
                        "EMPTY_FILE" ||
                    errorCode ===
                        "INVALID_DOCUMENT_TYPE"
                ) {

                    setStep(
                        "stepValidation",
                        "failed"
                    );

                } else if (
                    errorCode ===
                        "AI_QUOTA_EXCEEDED" ||
                    errorCode ===
                        "AI_SERVICE_UNAVAILABLE"
                ) {

                    setStep(
                        "stepValidation",
                        "complete"
                    );

                    setStep(
                        "stepExtraction",
                        "complete"
                    );

                    setStep(
                        "stepAI",
                        "failed"
                    );
                }

                throw new Error(
                    result.detail?.message ||
                    "Document processing failed."
                );
            }

            updateProcessingSteps(
                result
            );

            message.textContent =
                "Document processed successfully.";

            await loadDocuments();

            window.location.href =
                `/documents/${encodeURIComponent(
                    result.document_name
                )}`;

        } catch (error) {

            console.error(error);

            message.textContent =
                error.message;

        } finally {

            processButton.disabled =
                false;
        }
    }
);


refreshDocuments.addEventListener(
    "click",
    loadDocuments
);


loadDocuments();