import client from './client'

export interface Project {
  id: number
  name: string
  description: string | null
  created_at: string
}

export interface ProjectPayload {
  name: string
  description?: string | null
}

export async function getProjects(): Promise<Project[]> {
  return (await client.get<Project[]>('/projects')).data
}

export async function getProject(id: number): Promise<Project> {
  return (await client.get<Project>(`/projects/${id}`)).data
}

export async function createProject(payload: ProjectPayload): Promise<Project> {
  return (await client.post<Project>('/projects', payload)).data
}

export async function updateProject(id: number, payload: ProjectPayload): Promise<Project> {
  return (await client.put<Project>(`/projects/${id}`, payload)).data
}

export async function deleteProject(id: number): Promise<void> {
  await client.delete(`/projects/${id}`)
}
