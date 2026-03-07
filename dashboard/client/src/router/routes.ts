import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
    {
        path: '/',
        component: () => import('layouts/MainLayout.vue'),
        children: [
            { path: '', component: () => import('pages/SurveyList.vue') },
            { path: 'survey/new', component: () => import('pages/SurveyForm.vue') },
            { path: 'survey/:id/edit', component: () => import('pages/SurveyForm.vue') },
            { path: 'survey/:id', component: () => import('pages/SurveyDetail.vue') },
            { path: 'survey/:id/logs', component: () => import('pages/SyncLogs.vue') },
            { path: 'survey/:id/visualizations', component: () => import('pages/SurveyVisualizations.vue') },
        ],
    },
    {
        path: '/:catchAll(.*)*',
        component: () => import('pages/ErrorNotFound.vue'),
    },
];

export default routes;
