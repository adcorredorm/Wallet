/**
 * Category type definitions
 * Represents income/expense categories with optional hierarchy
 */

export enum CategoryType {
  INGRESO = 'ingreso',
  GASTO = 'gasto',
  AMBOS = 'ambos'
}

export interface Category {
  id: string
  nombre: string
  tipo: CategoryType
  icono?: string
  color?: string  // Hex color code (#RRGGBB)
  categoria_padre_id?: string
  created_at: string
  updated_at: string
}

export interface CreateCategoryDto {
  nombre: string
  tipo: CategoryType
  icono?: string
  color?: string
  categoria_padre_id?: string
}

export interface UpdateCategoryDto {
  nombre?: string
  tipo?: CategoryType
  icono?: string
  color?: string
  categoria_padre_id?: string
}
