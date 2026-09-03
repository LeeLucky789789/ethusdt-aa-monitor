import json

def play_sound(grade="A",cfg=None):
    # Cloud environments cannot play sound on the user's OS directly.
    return

def desktop_notify(title,message,enabled=True):
    # Disabled in Streamlit Cloud; browser notification is used instead.
    return

def browser_alert_html(title,message,grade="A",enabled=True):
    if not enabled:
        return ""
    st=json.dumps(title); sm=json.dumps(message); freq=1320 if grade=="A+" else 880
    return f"""<script>
    (async()=>{{try{{
      if('Notification' in window && Notification.permission==='granted') {{
        new Notification({st},{{body:{sm}}});
      }}
      const C=window.AudioContext||window.webkitAudioContext;
      if(C){{
        const c=new C(),o=c.createOscillator(),g=c.createGain();
        o.frequency.value={freq}; g.gain.value=.06;
        o.connect(g); g.connect(c.destination); o.start();
        setTimeout(()=>{{o.stop();c.close();}},650);
      }}
    }}catch(e){{}}}})();
    </script>"""

def permission_button_html():
    return """<button onclick="enableA()" style="padding:8px 14px;border-radius:8px;border:1px solid #999;cursor:pointer">Enable browser alerts</button>
    <span id="s" style="margin-left:8px;font-family:sans-serif"></span>
    <script>
    async function enableA(){const s=document.getElementById('s');try{
      if('Notification' in window){const p=await Notification.requestPermission();s.innerText='Permission: '+p;}
      const C=window.AudioContext||window.webkitAudioContext;
      if(C){const c=new C(),o=c.createOscillator(),g=c.createGain();o.frequency.value=880;g.gain.value=.05;o.connect(g);g.connect(c.destination);o.start();setTimeout(()=>{o.stop();c.close();},250);}
    }catch(e){s.innerText='Enable failed';}}
    </script>"""
