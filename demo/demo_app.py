import gradio as gr
import requests
import json

EXAMPLE_LOGS = {
    "Intrusion Detection/Prevention System)": '''
{\"timestamp\":\"2024-10-20T14:51:25.748189+0000\",\"flow_id\":1524601716776900,\"in_iface\":\"ens5\",\"event_type\":\"alert\",\"src_ip\":\"192.168.1.183\",\"src_port\":57044,\"dest_ip\":\"8.8.8.8\",\"dest_port\":53,\"proto\":\"UDP\",\"pkt_src\":\"wire/pcap\",\"community_id\":\"1:qMrb9UrubfWUPNejuMe3l34rbMA=\",\"tx_id\":0,\"alert\":{\"action\":\"allowed\",\"gid\":1,\"signature_id\":2030547,\"rev\":2,\"signature\":\"ET INFO Suspicious Outbound SIG DNS Query\",\"category\":\"Potentially Bad Traffic\",\"severity\":2,\"metadata\":{\"created_at\":[\"2020_07_16\"],\"performance_impact\":[\"Significant\"],\"signature_severity\":[\"Informational\"],\"updated_at\":[\"2020_11_17\"]}},\"dns\":{\"query\":[{\"type\":\"query\",\"id\":17405,\"rrname\":\"9.ibrokethe.net\",\"rrtype\":\"SIG\",\"tx_id\":0,\"opcode\":0}]},\"app_proto\":\"dns\",\"direction\":\"to_server\",\"flow\":{\"pkts_toserver\":1,\"pkts_toclient\":0,\"bytes_toserver\":86,\"bytes_toclient\":0,\"start\":\"2024-10-20T14:51:25.748189+0000\",\"src_ip\":\"192.168.1.183\",\"dest_ip\":\"8.8.8.8\",\"src_port\":57044,\"dest_port\":53},\"payload_printable\":\"C............9.ibrokethe.net.......)........\",\"stream\":0,\"capture_file\":\"/opt/engine/logs/engine01//alert_log.pcap.1.1729020751\",\"host\":\"engine-01\"}
''',
    
    "Web Application Firewall Logs": '''
2024-03-15T10:15:22Z WAF[67890]: detected XSS attempt from 203.0.113.1 - POST /login.php - payload: <script>alert(1)</script>
2024-03-15T10:15:23Z WAF[67890]: blocked SQL injection attempt from 203.0.113.1 - GET /products.php?id=1' OR '1'='1
2024-03-15T10:15:25Z WAF[67890]: rate limit exceeded for IP 203.0.113.1 - 100 requests in 60 seconds
2024-03-15T10:15:30Z WAF[67890]: blocked path traversal attempt from 203.0.113.1 - GET /../../etc/passwd
2024-03-15T10:15:35Z WAF[67890]: suspicious user agent detected from 203.0.113.1 - sqlmap/1.4.7
''',
    
    "Windows Security Events": '''
2024-03-15T14:45:10Z Security[4625]: An account failed to log on.
    Subject:
        Security ID: NULL SID
        Account Name: -
        Account Domain: -
        Logon ID: 0x0
    Failure Information:
        Failure Reason: Unknown user name or bad password
        Status: 0xC000006D
        Sub Status: 0xC0000064
    Process Information:
        Caller Process ID: 0x0
        Caller Process Name: -
    Network Information:
        Workstation Name: WIN-CLIENT01
        Source Network Address: 10.0.0.50
        Source Port: 52734
'''
}

class SecurityChatBot:
    def __init__(self, api_url="http://localhost:8019/enrich_llm"):
        self.api_url = api_url
        self.context = ""
        
    def query_api(self, query, context):
        headers = {
            'accept': 'application/json',
            'X-Request-ID': 'gradio-chat',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "query": query,
            "context": context
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["enriched_response"]
        except requests.exceptions.RequestException as e:
            return f"Error communicating with API: {str(e)}"

def create_chat_interface():
    chatbot = SecurityChatBot()
    
    def load_example(example_name):
        return EXAMPLE_LOGS[example_name]
            
    def load_log_context(logs):
        chatbot.context = logs
        return [], "Context loaded successfully. You can now ask questions about the logs."
            
    def respond(message, history):
        if not message:
            return history, ""
            
        response = chatbot.query_api(message, chatbot.context)
        
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})
        return history, ""
            
    def clear_chat():
        return [], ""
    
    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        gr.Markdown("# Security Log Analysis Chat Interface")
        
        with gr.Row():
            with gr.Column(scale=2):
                # Log input area
                log_input = gr.Textbox(
                    label="Security Log Context",
                    placeholder="Paste your security logs here or use the example buttons below...",
                    lines=10
                )
                
                with gr.Row():
                    # Example buttons
                    gr.Markdown("### Example Logs")
                    for name in EXAMPLE_LOGS.keys():
                        btn = gr.Button(name)
                        btn.click(
                            lambda n=name: EXAMPLE_LOGS[n],
                            None,
                            log_input
                        )
                
                load_context = gr.Button("Load Context")
                
                chatbot_interface = gr.Chatbot(
                    label="Chat History",
                    height=400,
                    type="messages"  
                )
                msg = gr.Textbox(
                    label="Ask about the logs or general security questions",
                    placeholder="Type your question here...",
                    lines=2
                )
                with gr.Row():
                    submit = gr.Button("Send")
                    clear = gr.Button("Clear Chat")

        # Event handlers
        load_context.click(
            load_log_context,
            inputs=[log_input],
            outputs=[chatbot_interface, msg]
        )
        
        submit.click(
            respond,
            inputs=[msg, chatbot_interface],
            outputs=[chatbot_interface, msg]
        )
        
        msg.submit(
            respond,
            inputs=[msg, chatbot_interface],
            outputs=[chatbot_interface, msg]
        )
        
        clear.click(
            clear_chat,
            outputs=[chatbot_interface, msg]
        )
        
    return demo

if __name__ == "__main__":
    demo = create_chat_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=True)