pipeline {
	agent { docker { image 'python:3.10-slim' } }

	environment {
		REGISTRY     = credentials('gcr-service-account-json')
		PROJECT_ID   = env.GCP_PROJECT_ID ?: 'your-project-id'
		REGION       = env.GCP_REGION ?: 'asia-southeast1'
		IMAGE_NAME   = 'hust-rag-chatbot'
		IMAGE_TAG    = "${env.BUILD_NUMBER}"
		CHART_PATH   = 'rag-controller/helm-charts/rag-chatbot'
		RELEASE_NAME = 'rag-chatbot'
		NAMESPACE    = env.K8S_NAMESPACE ?: 'rag'
	}

	options {
		ansiColor('xterm')
		timestamps()
	}

	stages {
		stage('Checkout') {
			steps { checkout scm }
		}

		stage('Install') {
			steps {
				sh 'python -m pip install --upgrade pip'
				sh 'pip install -r requirements.txt'
			}
		}

		stage('Lint') {
			steps { sh 'python -m compileall src' }
		}

		stage('Test') {
			steps { sh 'python -m unittest tests.test' }
		}

		stage('Build Image') {
			steps {
				sh '''
				echo "$REGISTRY" > key.json
				gcloud auth activate-service-account --key-file=key.json
				gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
				docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/chatbot/${IMAGE_NAME}:${IMAGE_TAG} .
				docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/chatbot/${IMAGE_NAME}:${IMAGE_TAG}
				'''
			}
		}

		stage('Deploy') {
			steps {
				sh '''
				echo "$REGISTRY" > key.json
				gcloud auth activate-service-account --key-file=key.json
				gcloud container clusters get-credentials rag-chatbot-gke --region ${REGION} --project ${PROJECT_ID}
				helm upgrade --install ${RELEASE_NAME} ${CHART_PATH} \
				  --namespace ${NAMESPACE} --create-namespace \
				  --set image.repository=${REGION}-docker.pkg.dev/${PROJECT_ID}/chatbot/${IMAGE_NAME} \
				  --set image.tag=${IMAGE_TAG}
				'''
			}
		}
	}
}
