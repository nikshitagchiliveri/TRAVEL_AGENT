import streamlit as st
import requests
import time
from typing import Dict, Any
from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

# Set page config
st.set_page_config(
    page_title="Travel Assistant",
    page_icon="✈️",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #0D47A1;
    }
    .destination-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .result-container {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        border: 1px solid #e0e0e0;
        margin-top: 20px;
    }
    .footer {
        text-align: center;
        margin-top: 30px;
        font-size: 0.8rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# App header
col1, col2 = st.columns([1, 4])
with col1:
    st.image("https://www.clipartmax.com/png/small/171-1712141_travel-icon-png.png", width=100)
with col2:
    st.markdown('<p class="main-header">Travel Assistant</p>', unsafe_allow_html=True)
    st.markdown("Discover weather conditions and top attractions for your next adventure!")

# Create tabs for the main content
tab1, tab2 = st.tabs(["Travel Planner", "Settings & Help"])

with tab1:
    # Input section with card styling
    st.markdown('<div class="destination-card">', unsafe_allow_html=True)
    
    # Destination input with autocomplete suggestions
    destination_options = ["Paris, France", "Tokyo, Japan", "New York, USA", "Rome, Italy", "Sydney, Australia"]
    destination = st.selectbox(
        "Where would you like to go?",
        options=[""] + destination_options,
        index=0,
        placeholder="Type or select a destination"
    )
    
    # Custom destination input if not in the suggestions
    if not destination:
        custom_destination = st.text_input("Or enter any destination:")
        if custom_destination:
            destination = custom_destination
    
    # Add travel date picker (for UI only - not used in API calls)
    col1, col2 = st.columns(2)
    with col1:
        travel_date = st.date_input("When are you planning to visit?")
    with col2:
        travel_duration = st.slider("How many days?", 1, 30, 7)
    
    # Travel interests (for a more personalized experience - not used in current API implementation)
    interests = st.multiselect(
        "What are you interested in?",
        ["Historical Sites", "Museums", "Food & Dining", "Nature", "Shopping", "Nightlife", "Family Activities"],
        default=["Historical Sites", "Food & Dining"]
    )
    
    submit_button = st.button("Plan My Trip", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Results section
    if "travel_results" in st.session_state:
        st.markdown('<div class="result-container">', unsafe_allow_html=True)
        st.markdown(f'<p class="sub-header">Your Travel Plan for {destination}</p>', unsafe_allow_html=True)
        st.markdown(st.session_state.travel_results)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Add a map of the destination
        st.subheader("Destination Map")
        try:
            st.map()  # This would ideally use geocoding to pinpoint the exact location
        except:
            st.info("Map visualization is currently unavailable.")
    
with tab2:
    # Settings section
    st.subheader("API Configuration")
    
    # Use expanders to save space
    with st.expander("API Keys (Required)", expanded=True):
        GOOGLE_API_KEY = st.text_input("Google Gemini API Key", type="password", 
                                      help="Required for the language model")
        TAVILY_API_KEY = st.text_input("Tavily API Key", type="password", 
                                      help="Required for attraction search")
        WEATHER_API_KEY = st.text_input("Weather API Key", type="password", 
                                      help="Required for weather information")
        
        st.info("These keys are not stored and will need to be re-entered if you refresh the page.")
    
    # Help section
    with st.expander("How to Get API Keys"):
        st.markdown("""
        To use this application, you need to obtain the following API keys:
        
        1. **Google API Key**: Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
        2. **Tavily API Key**: Register for an API key at [Tavily](https://tavily.com/#api)
        3. **Weather API Key**: Sign up for a free API key at [WeatherAPI](https://www.weatherapi.com/)
        """)
    
    with st.expander("About This App"):
        st.markdown("""
        This Travel Assistant helps you plan your trips by providing:
        
        - Current weather information for your destination
        - Top attractions and things to do
        - Personalized recommendations based on your interests
        
        The app uses LangChain with Google's Gemini model for intelligent responses,
        WeatherAPI for real-time weather data, and Tavily for up-to-date attraction information.
        """)

# Function to create the travel assistant
def create_travel_assistant():
    # Create a custom tool for weather information
    @tool
    def get_weather(location: str) -> Dict[str, Any]:
        """Get current weather for a location."""
        try:
            url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={location}&aqi=no"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            weather_info = {
                "location": f"{data['location']['name']}, {data['location']['country']}",
                "temperature_c": data['current']['temp_c'],
                "temperature_f": data['current']['temp_f'],
                "condition": data['current']['condition']['text'],
                "humidity": data['current']['humidity'],
                "wind_kph": data['current']['wind_kph'],
                "feels_like_c": data['current']['feelslike_c'],
                "feels_like_f": data['current']['feelslike_f'],
                "last_updated": data['current']['last_updated']
            }
            return weather_info
        except Exception as e:
            return {"error": f"Failed to get weather information: {str(e)}"}

    # Create a tool for attractions search
    @tool
    def search_attractions(location: str) -> str:
        """Search for top tourist attractions in a location."""
        # Set Tavily API key
        import os
        os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY
        
        search_tool = TavilySearchResults(k=5)
        results = search_tool.invoke(f"Top tourist attractions and places to visit in {location}")
        
        # Format the results
        formatted_results = "Top Attractions:\n\n"
        for i, result in enumerate(results, 1):
            formatted_results += f"{i}. {result.get('title', 'No title')}\n"
            formatted_results += f"   {result.get('content', 'No description')}\n\n"
        
        return formatted_results

    # Set up the LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-001",
        temperature=0.3,
        google_api_key=GOOGLE_API_KEY
    )

    # Create a prompt that includes user interests
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful travel assistant that provides information about destinations.
        When a user asks about a location, you need to:
        1. Get the current weather information for that location
        2. Find top tourist attractions to visit
        3. Present this information in a clear and organized way with markdown formatting
        
        Format your response with clear headings, emoji icons where appropriate, and make sure
        it's visually appealing when rendered in markdown.
        
        Include a brief introduction about the destination and a personalized conclusion.
        """),
        ("human", "{input}"),
        ("assistant", "{agent_scratchpad}")
    ])

    # Create tools list
    tools = [get_weather, search_attractions]

    # Create the agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)
    
    return agent_executor

# Function to run the travel assistant
def run_travel_assistant(destination: str, interests: list, agent_executor):
    interests_str = ", ".join(interests) if interests else "general sightseeing"
    response = agent_executor.invoke({
        "input": f"I'm planning to visit {destination}. I'm interested in {interests_str}. What's the weather like and what are some attractions I should see?"
    })
    return response["output"]

# Main app flow for handling the button click
if submit_button and destination:
    # Check if API keys are provided
    if not all([GOOGLE_API_KEY, TAVILY_API_KEY, WEATHER_API_KEY]):
        st.error("⚠️ Please provide all required API keys in the Settings tab.")
    else:
        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Update progress
            status_text.text("Creating your travel assistant...")
            progress_bar.progress(25)
            time.sleep(0.5)
            
            # Create the assistant
            agent_executor = create_travel_assistant()
            
            # Update progress
            status_text.text("Searching for weather information...")
            progress_bar.progress(50)
            time.sleep(0.5)
            
            # Update progress
            status_text.text("Finding top attractions...")
            progress_bar.progress(75)
            time.sleep(0.5)
            
            # Get the result
            result = run_travel_assistant(destination, interests, agent_executor)
            
            # Update progress
            status_text.text("Finalizing your travel plan...")
            progress_bar.progress(100)
            time.sleep(0.5)
            
            # Clear the progress indicators
            status_text.empty()
            progress_bar.empty()
            
            # Store and display the result
            st.session_state.travel_results = result
            
            # Force a rerun to display the results
            st.experimental_rerun()
            
        except Exception as e:
            # Clear the progress indicators
            status_text.empty()
            progress_bar.empty()
            
            st.error(f"An error occurred: {str(e)}")
            st.info("Please check your API keys and try again.")

# Footer
st.markdown('<div class="footer">Travel Assistant App | Created with Streamlit and LangChain</div>', unsafe_allow_html=True)
