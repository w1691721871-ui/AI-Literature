from pydantic import BaseModel, Field
class OrganizationCreate(BaseModel):
    name:str=Field(min_length=1,max_length=200)
    admin_name:str=Field(min_length=1,max_length=120)
class PermissionRequest(BaseModel):
    member_id:str
    permission:str


class OrganizationMemberCreate(BaseModel):
    member_id: str
    display_name: str = Field(min_length=1, max_length=120)
    role: str = Field(pattern="^(Researcher|Reviewer|Leader|Admin)$")


class OrganizationProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    description: str = ""
    research_goal: str = ""
    owner_member_id: str
    research_project_id: str | None = None
    workspace_id: str | None = None


class ProjectStatusUpdate(BaseModel):
    member_id: str
    status: str = Field(pattern="^(Planning|Researching|Reviewing|Delivering|Completed)$")


class KnowledgeScopeUpdate(BaseModel):
    member_id: str
    paper_id: str
    knowledge_scope: str = Field(pattern="^(Private|Team|Organization)$")


class MeetingCreate(BaseModel):
    member_id: str
    notes: str = Field(min_length=1, max_length=10000)
    project_id: str | None = None
