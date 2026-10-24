import client from './client'
import type { MappingBinding, MappingTemplate } from '../utils/mapping-templates'
export type { MappingTemplate } from '../utils/mapping-templates'

const base = (projectId: number) => `/projects/${projectId}/result-mapping-templates`
export async function getMappingTemplates(projectId: number): Promise<MappingTemplate[]> {
  return (await client.get<MappingTemplate[]>(base(projectId))).data
}
export async function saveMappingTemplate(projectId: number, name: string, mappings: MappingBinding[], id?: number): Promise<MappingTemplate> {
  const payload = { name, mappings }
  return (await (id === undefined ? client.post<MappingTemplate>(base(projectId), payload)
    : client.put<MappingTemplate>(`${base(projectId)}/${id}`, payload))).data
}
export async function renameMappingTemplate(projectId: number, id: number, name: string): Promise<MappingTemplate> {
  return (await client.patch<MappingTemplate>(`${base(projectId)}/${id}`, { name })).data
}
export async function deleteMappingTemplate(projectId: number, id: number): Promise<void> {
  await client.delete(`${base(projectId)}/${id}`)
}
