# Prototipo

| Componente | Dónde está | Estado |
| --- | --- | --- |
| Plataforma multiagente (frontend) | [`frontend/`](../frontend) · https://learn-multiagent.vercel.app | Desplegado en Vercel |
| Plataforma multiagente (backend, Orquestador y agentes) | [`backend/`](../backend) · https://learn-multiagent.onrender.com/health | Desplegado en Render |
| Mando de respuestas (IoT) | [`mando_wokwi/`](mando_wokwi) | Simulado en Wokwi |
| Agente de refuerzo en Make (No-Code) | Capturas en [`Evidencias/04_Automatizacion_Make`](../Evidencias/04_Automatizacion_Make) | Probado por separado |
| Isla Aprende (AR, VR y metaverso) | https://github.com/Giuseppi05/learn-island · https://giuseppi05.github.io/learn-island/ | Maqueta publicada con datos simulados |

La plataforma ya tiene el endpoint `POST /devices/events` para recibir los eventos del mando y de Isla Aprende. Conectar ambos canales a ese endpoint es la siguiente etapa (Sección 18.4 del informe).
