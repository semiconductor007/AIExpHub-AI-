import client from './client'

export interface HealthResponse {
  status: string
  service: string
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await client.get<HealthResponse>('/health')
  return response.data
}
