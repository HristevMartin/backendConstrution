import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from queries import DashboardQueries
from datetime import datetime
import pandas as pd

# Page config
st.set_page_config(
    page_title="Page Visits Dashboard",
    page_icon="📊",
    layout="wide"
)

# Initialize queries
@st.cache_resource
def get_queries():
    return DashboardQueries()

queries = get_queries()

# Title
st.title("📊 Page Visits Dashboard")
st.markdown("---")

# Refresh button
if st.button("🔄 Refresh Data"):
    st.cache_resource.clear()
    st.rerun()

# Key Metrics Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_visits = queries.get_total_visits()
    st.metric("Total Visits", f"{total_visits:,}")

with col2:
    unique_visitors = queries.get_unique_visitors()
    st.metric("Unique Visitors", f"{unique_visitors:,}")

with col3:
    # Calculate average pages per visitor
    avg_pages = total_visits / unique_visitors if unique_visitors > 0 else 0
    st.metric("Avg Pages/Visitor", f"{avg_pages:.2f}")

with col4:
    st.metric("Database", "travelDB")

st.markdown("---")

# Two column layout
col_left, col_right = st.columns(2)

with col_left:
    # Visits over time
    st.subheader("📈 Visits Over Time")
    days = st.selectbox("Time Period", [7, 14, 30], key="time_period")
    visits_time = queries.get_visits_over_time(days=days)
    
    if not visits_time.empty:
        fig = px.line(
            visits_time, 
            x='date', 
            y='count',
            title=f'Page Visits (Last {days} Days)',
            labels={'count': 'Visits', 'date': 'Date'}
        )
        fig.update_traces(line_color='#1f77b4', line_width=3)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for selected time period")


st.markdown("---")

# Device & Browser Analytics
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📱 Device Types")
    device_data = queries.get_device_breakdown()
    
    if not device_data.empty:
        fig = px.pie(
            device_data,
            values='count',
            names='device_type',
            title='Device Distribution'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No device data available")

with col2:
    st.subheader("🌐 Browsers")
    browser_data = queries.get_browser_breakdown()
    
    if not browser_data.empty:
        fig = px.pie(
            browser_data,
            values='count',
            names='browser',
            title='Browser Distribution'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No browser data available")

with col3:
    st.subheader("💻 Operating Systems")
    os_data = queries.get_os_breakdown()
    
    if not os_data.empty:
        fig = px.pie(
            os_data,
            values='count',
            names='os',
            title='OS Distribution'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No OS data available")

st.markdown("---")

# Top Referrers
st.subheader("🔗 Top Referrers")
referrers = queries.get_top_referrers()

if not referrers.empty:
    fig = px.bar(
        referrers,
        x='count',
        y='referrer',
        orientation='h',
        title='Top Traffic Sources',
        labels={'count': 'Visits', 'referrer': 'Referrer'}
    )
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No referrer data available")

st.markdown("---")

# Unique IP Addresses for Home Page
st.subheader("🏠 Home Page Visitors")

col1, col2 = st.columns([2, 1])

with col1:
    st.write("**Unique IP Addresses Accessing Home Page**")
    home_ips = queries.get_unique_ips_by_page("home")
    
    if not home_ips.empty:
        # Format the dataframe for display
        display_df = home_ips.copy()
        display_df['last_visit'] = pd.to_datetime(display_df['last_visit']).dt.strftime('%Y-%m-%d %H:%M:%S')
        display_df['first_visit'] = pd.to_datetime(display_df['first_visit']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        st.dataframe(
            display_df[['ip_address', 'visit_count', 'last_visit', 'first_visit']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "ip_address": "IP Address",
                "visit_count": st.column_config.NumberColumn(
                    "Visit Count",
                    format="%d"
                ),
                "last_visit": "Last Visit",
                "first_visit": "First Visit"
            }
        )
        
        # Summary metrics
        st.write(f"**Total unique visitors to home page:** {len(home_ips)}")
        st.write(f"**Total home page visits:** {home_ips['visit_count'].sum()}")
    else:
        st.info("No visitors to home page yet")

with col2:
    st.write("**Top 5 Most Frequent Visitors**")
    if not home_ips.empty:
        top_5 = home_ips.head(5)
        fig = px.bar(
            top_5,
            x='visit_count',
            y='ip_address',
            orientation='h',
            title='Most Active IPs on Home',
            labels={'visit_count': 'Visits', 'ip_address': 'IP Address'}
        )
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available")

# Optional: IP Address Details Expander
with st.expander("🔍 View Details for Specific IP"):
    if not home_ips.empty:
        selected_ip = st.selectbox(
            "Select an IP address to view their activity:",
            options=home_ips['ip_address'].tolist()
        )
        
        if selected_ip:
            ip_details = queries.get_visitor_details_by_ip(selected_ip)
            
            st.write(f"**Activity for IP: {selected_ip}**")
            st.write(f"Total visits across all pages: {len(ip_details)}")
            
            # Pages visited by this IP
            pages_visited = ip_details.groupby('page').size().reset_index(name='count')
            pages_visited = pages_visited.sort_values('count', ascending=False)
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.write("**Pages Visited:**")
                st.dataframe(
                    pages_visited,
                    use_container_width=True,
                    hide_index=True
                )
            
            with col_b:
                # Device info
                if 'device_type' in ip_details.columns:
                    st.write(f"**Device Type:** {ip_details['device_type'].iloc[0]}")
                if 'browser' in ip_details.columns:
                    st.write(f"**Browser:** {ip_details['browser'].iloc[0]}")
                if 'os' in ip_details.columns:
                    st.write(f"**OS:** {ip_details['os'].iloc[0]}")

st.markdown("---")

# Recent Visits Table
st.subheader("🕐 Recent Visits")
recent_visits = queries.get_recent_visits(limit=20)

if not recent_visits.empty:
    # Select and format columns
    display_columns = ['page', 'url', 'device_type', 'browser', 'os', 'created_at']
    available_columns = [col for col in display_columns if col in recent_visits.columns]
    
    st.dataframe(
        recent_visits[available_columns],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No recent visits available")

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")