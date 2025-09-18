from resources.auth import (
    Register,
    Login,
    Test,
    Logout,
)

from resources.TraderForm import TraderForm
from resources.UserTrack import UserTrack
from resources.TraderProject import SaveProject, UpdateProject
from resources.User import GetUser, SaveUserRole, GetUserRole
from resources.GetProjectServices import GetProjectServices, GetSpecificServices
from resources.StaticFiles import ServeUploadedFile
from resources.TraderProject import GetProjectByID
from resources.TraderForm import GetProfileByID
from resources.TraderProject import GetAllProfiles
from resources.CommentResource import SaveComment, GetCommentsByProjectId, DeleteComment, UpdateComment
from resources.ClientProjects import ClientProjects, GetClientProject, EditClientProject, GetAllClientProjects
from resources.TraderProjects import SaveTraderProject, GetTraderProject
from resources.Payments import PayWithStripe, CheckPaymentStatus
from resources.ChatComponent import ChatComponent, CreateChat, GetAllChats


routes = [
    (Register, "/travel/register"),
    (Login, "/travel/login"),
    (Logout, "/travel/logout"),
    (ClientProjects, "/travel/save-client-project"),
    (GetClientProject, "/travel/get-client-project/<project_id>"),
    (EditClientProject, "/travel/edit-client-project/<project_id>"),
    (SaveTraderProject, "/travel/save-trader-project"),
    (GetTraderProject, "/travel/get-trader-project/<user_id>"),
    (GetUserRole, "/travel/get-user-role"),
    (GetAllClientProjects, "/travel/get-all-client-projects"),
    (PayWithStripe, "/api/payments/create-intent"),
    (CheckPaymentStatus, "/api/payments/check-payment-status/<user_id>/<job_id>"),
    (ChatComponent, "/travel/chat-component/<conversation_id>"),
    (CreateChat, "/travel/chat-component/create-chat"),
    (GetAllChats, "/travel/chat-component/get-all-chats/<user_id>"),
]
