import { create } from 'zustand'
import type { UserProfile, Roadmap } from '@/lib/types'

interface UserState {
  userId: string | null
  name: string
  skills: string[]
  githubUsername: string | null
  selectedRole: string | null
  readinessScores: Record<string, number>
  currentRoadmap: Roadmap | null
  isLoading: boolean
  
  setUser: (profile: UserProfile) => void
  setSkills: (skills: string[]) => void
  addSkill: (skill: string) => void
  removeSkill: (skill: string) => void
  setGithubUsername: (username: string | null) => void
  setSelectedRole: (role: string | null) => void
  setReadinessScores: (scores: Record<string, number>) => void
  setRoadmap: (roadmap: Roadmap | null) => void
  setLoading: (loading: boolean) => void
  reset: () => void
}

const initialState = {
  userId: null,
  name: 'Guest User',
  skills: [],
  githubUsername: null,
  selectedRole: null,
  readinessScores: {},
  currentRoadmap: null,
  isLoading: false,
}

export const useUserStore = create<UserState>((set) => ({
  ...initialState,

  setUser: (profile: UserProfile) => set({
    userId: profile.id,
    name: profile.name,
    skills: profile.skills,
    githubUsername: profile.github?.username || null,
  }),

  setSkills: (skills: string[]) => set({ skills }),

  addSkill: (skill: string) => set((state) => ({
    skills: state.skills.includes(skill) ? state.skills : [...state.skills, skill],
  })),

  removeSkill: (skill: string) => set((state) => ({
    skills: state.skills.filter((s) => s !== skill),
  })),

  setGithubUsername: (username: string | null) => set({ githubUsername: username }),

  setSelectedRole: (role: string | null) => set({ selectedRole: role }),

  setReadinessScores: (scores: Record<string, number>) => set({ readinessScores: scores }),

  setRoadmap: (roadmap: Roadmap | null) => set({ currentRoadmap: roadmap }),

  setLoading: (loading: boolean) => set({ isLoading: loading }),

  reset: () => set(initialState),
}))
