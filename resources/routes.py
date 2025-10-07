from resources.auth import (
    Register,
    Login,
    Test,
    Logout,
    ForgotPassword,
    ResetPassword,
    GetSession,
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
from resources.ClientProjects import ClientProjects, GetClientProject, EditClientProject, GetAllClientProjects, DeleteClientProjectId
from resources.TraderProjects import SaveTraderProject, GetTraderProject
from resources.Payments import PayWithStripe, CheckPaymentStatus
from resources.ChatComponent import ChatComponent, CreateChat, GetAllChats, GetConversationById, ChatSummary, MarkConversationRead
from resources.track_visits import SimplePageTrackingResource, GetPageVisits
from resources.JobApplicationCounter import JobApplicationCounterResource
from resources.User import GetUserData, PostUserRadiusKm
from resources.ai_helper import AIHelper, AITraderHelper
from resources.ClientCompletedJobs import GetClientCompletedJobs, GetAllClientStatusProjects
from resources.trader_rating import TraderRating


routes = [
    (Register, "/travel/register"),
    (Login, "/travel/login"),
    (Logout, "/travel/logout"),
    (ForgotPassword, "/travel/forgot-password"),
    (ClientProjects, "/travel/save-client-project"),
    (GetClientProject, "/travel/get-client-project/<project_id>"),
    (EditClientProject, "/travel/edit-client-project/<project_id>"),
    (DeleteClientProjectId, "/travel/delete-client-project/<project_id>"),
    (SaveTraderProject, "/travel/save-trader-project"),
    (GetTraderProject, "/travel/get-trader-project/<user_id>"),
    (GetUserRole, "/travel/get-user-role"),
    (GetUserData, "/travel/get-user-data"),
    (PostUserRadiusKm, "/travel/post-user-radius-km"),
    (GetAllClientProjects, "/travel/get-all-client-projects"),
    (PayWithStripe, "/api/payments/create-intent"),
    (CheckPaymentStatus, "/api/payments/check-payment-status/<user_id>/<job_id>"),
    (ChatComponent, "/travel/chat-component/<conversation_id>"),
    (CreateChat, "/travel/chat-component/create-chat"),
    (GetAllChats, "/travel/chat-component/get-all-chats"),
    (GetConversationById, "/travel/chat-component/get-conversation-by-id/<job_id>"),
    (ChatSummary, "/travel/chat-component/chat-summary"),
    (MarkConversationRead, "/travel/chat-component/mark-as-read/<conversation_id>"),
    (ResetPassword, "/travel/reset-password"),
    (GetSession, "/travel/auth/session"),
    (SimplePageTrackingResource, "/travel/track-visit"),
    (GetPageVisits, "/travel/page-visits"),
    (JobApplicationCounterResource, "/travel/job-application-counter/<job_id>"),
    (AIHelper, "/travel/ai-helper"),
    (AITraderHelper, "/travel/trader-helper"),
    (GetClientCompletedJobs, "/travel/get-client-completed-jobs/<job_id>"),
    (GetAllClientStatusProjects, "/travel/get-all-client-status-projects"),
    (TraderRating, "/travel/get-trader-completed-job")
]
