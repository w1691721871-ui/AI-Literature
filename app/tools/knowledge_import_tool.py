"""Safe import planner that directs users to the existing formal upload flow."""

from app.tools.file_operator import FileOperator


class KnowledgeImportTool:
    name = "knowledge_import_planner"
    description = "Finds local candidate files and prepares an approval-required import plan; it never writes the knowledge base directly."

    def __init__(self, file_operator: FileOperator | None = None) -> None:
        self._file_operator = file_operator or FileOperator()

    def prepare(self) -> dict[str, object]:
        inventory = self._file_operator.inspect()
        return {"status": "approval_required", "candidate_count": inventory["file_count"], "candidates": inventory["files"], "boundary": "请通过现有论文上传接口导入资料；本工具不会直接写入 SQLite、向量索引或 Embedding。"}
