FROM ollama/ollama:latest

# Создаём скрипт для автоматической загрузки модели при старте
RUN echo '#!/bin/bash' > /entrypoint.sh && \
    echo 'ollama serve &' >> /entrypoint.sh && \
    echo 'sleep 5' >> /entrypoint.sh && \
    echo 'ollama pull llama3.2:3b' >> /entrypoint.sh && \
    echo 'tail -f /dev/null' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

EXPOSE 11434

ENTRYPOINT ["/entrypoint.sh"]