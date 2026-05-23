import { createRouter, createWebHistory } from 'vue-router'
import NominatePage from './views/NominatePage.vue'
import AwardNominatePage from './views/AwardNominatePage.vue'
import CampaignVotePage from './views/CampaignVotePage.vue'
import AwardVotePage from './views/AwardVotePage.vue'
import FinalistSubmissionPage from './views/FinalistSubmissionPage.vue'
import NotFoundView from './views/NotFoundView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/nominate/:slug', name: 'nominate', component: NominatePage, props: true },
    { path: '/nominate/:slug/:awardSlug', name: 'nominate-award', component: AwardNominatePage, props: true },
    { path: '/vote/:slug', name: 'vote-campaign', component: CampaignVotePage, props: true },
    { path: '/vote/:slug/:awardSlug', name: 'vote-award', component: AwardVotePage, props: true },
    { path: '/finalist/:token', name: 'finalist-submission', component: FinalistSubmissionPage, props: true },
    { path: '/:pathMatch(.*)*', component: NotFoundView },
  ],
})
