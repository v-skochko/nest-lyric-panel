FROM node:22-bookworm-slim
WORKDIR /app
RUN npm install --onnxruntime-node-install-cuda=skip --omit=dev @huggingface/transformers@3.8.1
COPY server.mjs worker.mjs /app/
ENV HF_HOME=/model-cache
EXPOSE 5000
CMD ["node", "server.mjs"]
