import streamlit as st
import pandas as pd
import json
import requests
import time
import random
import os
from typing import Dict, Any, Optional

def validate_csv_structure(df: pd.DataFrame) -> bool:
    """Validates that the CSV has the required columns"""
    required_columns = ['id', 'channel', 'customer_name', 'subject', 'fullMessage', 'sentiment_name']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        st.error(f"❌ Missing columns in CSV: {', '.join(missing_columns)}")
        st.info("Required columns: id, channel, customer_name, subject, fullMessage, sentiment_name")
        return False
    return True

def create_ticket_payload(row: pd.Series) -> Dict[str, Any]:
    """Creates the JSON payload for a ticket"""
    return {
        "external_id": str(row['id']),
        "source_channel": str(row['channel']),
        "customer": {
            "name": str(row['customer_name'])
        },
        "content": {
            "subject": str(row['subject']),
            "body": str(row['fullMessage'])
        },
        "ai_analysis": {
            "sentiment": str(row['sentiment_name'])
        }
    }

def send_ticket(payload: Dict[str, Any], endpoint: str) -> tuple[bool, int, str]:
    """Sends a ticket to the endpoint and returns the status"""
    try:
        response = requests.post(
            endpoint, 
            json=payload, 
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )
        return True, response.status_code, response.text
    except requests.exceptions.RequestException as e:
        return False, 0, str(e)

def main():
    st.set_page_config(
        page_title="SupportFlow - Ticket Simulator",
        page_icon="🎫",
        layout="wide"
    )
    
    st.title("🎫 SupportFlow Ticket Simulator")
    st.markdown("---")
    
    # Usage information
    with st.expander("ℹ️ How to use"):
        st.markdown("""
        ### How to use this simulator:
        1. **Prepare your CSV file** with the following columns:
           - `id`: Unique ticket identifier
           - `channel`: Source channel (email, chat, phone, etc.)
           - `customer_name`: Customer name
           - `subject`: Ticket subject
           - `fullMessage`: Complete ticket message
           - `sentiment_name`: Detected sentiment (positive, negative, neutral)
        
        2. **Configure the endpoint** where you want to send the tickets (e.g.: webhook.site)
        
        3. **Upload the CSV file** and review the preview
        
        4. **Send the tickets** and monitor the progress
        """)
    
    # Columns to organize the interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📁 CSV File")
        csv_file = st.file_uploader(
            "Upload your CSV file with ticket data",
            type=["csv"],
            help="File must contain columns: id, channel, customer_name, subject, fullMessage, sentiment_name"
        )
    
    with col2:
        st.subheader("🌐 Configuration")
        endpoint = st.text_input(
            "Endpoint URL",
            placeholder="https://webhook.site/your-endpoint",
            help="URL where tickets will be sent"
        )
        
        # Additional configuration
        delay_min = st.slider("Minimum delay (seconds)", 0.1, 5.0, 0.5, 0.1)
        delay_max = st.slider("Maximum delay (seconds)", 0.1, 5.0, 1.5, 0.1)
    
    # CSV file processing
    if csv_file:
        try:
            df = pd.read_csv(csv_file)
            
            if validate_csv_structure(df):
                st.success(f"✅ Valid CSV loaded with {len(df)} tickets")
                
                # CSV preview
                st.subheader("👀 CSV Preview")
                st.dataframe(df, use_container_width=True)
                
                # Dataset statistics
                col_stats1, col_stats2, col_stats3 = st.columns(3)
                with col_stats1:
                    st.metric("Total tickets", int(len(df)))
                with col_stats2:
                    unique_channels = int(df['channel'].nunique())
                    st.metric("Unique channels", unique_channels)
                with col_stats3:
                    unique_customers = int(df['customer_name'].nunique())
                    st.metric("Unique customers", unique_customers)
                
                # Send button
                if endpoint:
                    st.markdown("---")
                    if st.button("🚀 Send Tickets", type="primary", use_container_width=True):
                        send_tickets_process(df, endpoint, delay_min, delay_max)
                else:
                    st.warning("⚠️ Please enter the endpoint URL to continue")
        
        except Exception as e:
            st.error(f"❌ Error processing CSV file: {str(e)}")

def send_tickets_process(df: pd.DataFrame, endpoint: str, delay_min: float, delay_max: float):
    """Processes the sending of all tickets"""
    total_tickets = len(df)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Containers to show results
    success_container = st.container()
    error_container = st.container()
    
    successful_sends = 0
    failed_sends = 0
    
    for i, (idx, row) in enumerate(df.iterrows()):
        # Update progress
        progress = (i + 1) / total_tickets
        progress_bar.progress(progress)
        status_text.text(f"Sending ticket {i + 1} of {total_tickets}...")
        
        # Create payload
        payload = create_ticket_payload(row)
        
        # Show payload in expandable section
        with st.expander(f"📋 Ticket {payload['external_id']} payload", expanded=False):
            st.code(json.dumps(payload, indent=2, ensure_ascii=False), language='json')
        
        # Send ticket
        success, status_code, response_text = send_ticket(payload, endpoint)
        
        if success:
            successful_sends += 1
            with success_container:
                st.success(f"✅ Ticket {payload['external_id']} sent successfully (Status: {status_code})")
        else:
            failed_sends += 1
            with error_container:
                st.error(f"❌ Error sending ticket {payload['external_id']}: {response_text}")
        
        # Delay between sends
        if i < total_tickets - 1:  # No delay after last ticket
            delay = random.uniform(delay_min, delay_max)
            time.sleep(delay)
    
    # Final summary
    progress_bar.progress(1.0)
    status_text.text("✅ Process completed")
    
    st.markdown("---")
    st.subheader("📊 Sending Summary")
    
    col_summary1, col_summary2, col_summary3 = st.columns(3)
    with col_summary1:
        st.metric("Successfully sent tickets", successful_sends)
    with col_summary2:
        st.metric("Failed tickets", failed_sends)
    with col_summary3:
        success_rate = (successful_sends / total_tickets) * 100 if total_tickets > 0 else 0
        st.metric("Success rate", f"{success_rate:.1f}%")
    
    if successful_sends == total_tickets:
        st.balloons()
        st.success("🎉 All tickets were sent successfully!")
    elif failed_sends > 0:
        st.warning(f"⚠️ Sending completed with {failed_sends} errors. Check details above.")

if __name__ == "__main__":
    main()
