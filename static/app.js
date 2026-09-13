const { createApp, ref, reactive, computed, onMounted, nextTick, watch } = Vue;

const app = createApp({
  setup() {
    const activeTab = ref('nodes');
    const currentTarget = ref('mihomo');
    const isSaving = ref(false);
    const isTestingAllDelays = ref(false);
    const isFetchingSub = ref(false);

    // Status
    const status = reactive({
      ssh_connected: false,
      mihomo_running: false,
      mihomo_api_ready: false,
      mihomo_version: '',
      config_path: '/vol1/1000/Docker/mihomo/config/config.yaml'
    });

    // Config Data
    const proxies = ref([]);
    const proxyGroups = ref([]);
    const rules = ref([]);
    const rawYaml = ref('');
    const delays = reactive({});
    const backups = ref([]);

    // Filter & Search
    const searchQuery = ref('');
    const selectedProtocol = ref('');

    // Toast
    const toast = reactive({
      show: false,
      message: '',
      type: 'success'
    });

    const showToast = (message, type = 'success') => {
      toast.message = message;
      toast.type = type;
      toast.show = true;
      setTimeout(() => {
        toast.show = false;
      }, 3500);
    };

    // Modals
    const showNodeModal = ref(false);
    const isEditingNode = ref(false);
    const editingNodeIndex = ref(-1);
    const quickLinkInput = ref('');

    const nodeForm = reactive({
      name: '',
      type: 'vless',
      server: '',
      port: 443,
      uuid: '',
      password: '',
      cipher: 'aes-256-gcm',
      auth: '',
      network: 'tcp',
      tls: true,
      flow: 'xtls-rprx-vision',
      servername: 'www.bing.com',
      is_reality: true,
      reality_pbk: '',
      reality_sid: '',
      client_fp: 'chrome',
      udp: true
    });

    const showBatchModal = ref(false);
    const batchInputText = ref('');
    const batchAddToProxyGroup = ref(true);

    const showSubModal = ref(false);
    const subUrlInput = ref('');
    const fetchedSubProxies = ref([]);
    const selectedSubIndices = ref([]);

    const showSettingsModal = ref(false);
    const settingsForm = reactive({
      ssh_host: '192.168.1.57',
      ssh_port: 22,
      ssh_user: 'admin',
      ssh_pass: '',
      remote_path: '/vol1/1000/Docker/mihomo/config/config.yaml',
      mihomo_api: 'http://192.168.1.57:9092',
      mihomo_secret: 'Yrxc_anB6B3sgINsZ9t-yNLCfeDium2n'
    });

    // Computed
    const filteredProxies = computed(() => {
      return proxies.value.filter(node => {
        if (!node || !node.name) return false;
        const matchesQuery = !searchQuery.value || 
          node.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
          (node.server && node.server.toLowerCase().includes(searchQuery.value.toLowerCase()));
        const matchesProtocol = !selectedProtocol.value || 
          (node.type && node.type.toLowerCase() === selectedProtocol.value.toLowerCase());
        return matchesQuery && matchesProtocol;
      });
    });

    const availableProxyNames = computed(() => {
      const names = proxies.value.map(p => p.name).filter(Boolean);
      return ['DIRECT', 'REJECT', ...names];
    });

    // Helper functions
    const refreshIcons = () => {
      nextTick(() => {
        if (window.lucide) {
          window.lucide.createIcons();
        }
      });
    };

    const getProtocolBadgeClass = (type) => {
      const t = (type || '').toLowerCase();
      if (t === 'vless') return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
      if (t === 'vmess') return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
      if (t === 'trojan') return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      if (t === 'ss') return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
      if (t.includes('hy')) return 'bg-rose-500/20 text-rose-300 border-rose-500/30';
      return 'bg-slate-700 text-slate-300 border-slate-600';
    };

    const getDelayBadgeClass = (delay) => {
      if (delay === undefined) return 'bg-slate-800 text-slate-400 hover:bg-slate-700';
      if (delay > 0 && delay < 300) return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
      if (delay >= 300 && delay < 800) return 'bg-amber-500/20 text-amber-300 border border-amber-500/30';
      return 'bg-red-500/20 text-red-300 border border-red-500/30';
    };

    const getDelayDotClass = (delay) => {
      if (delay === undefined) return 'bg-slate-500';
      if (delay > 0 && delay < 300) return 'bg-emerald-400';
      if (delay >= 300 && delay < 800) return 'bg-amber-400';
      return 'bg-red-400';
    };

    const parseRule = (ruleStr) => {
      if (typeof ruleStr !== 'string') return { type: 'RULE', payload: '', target: '' };
      const parts = ruleStr.split(',');
      return {
        type: parts[0] || 'MATCH',
        payload: parts.length > 2 ? parts[1] : '',
        target: parts.length > 2 ? parts[2] : (parts[1] || 'DIRECT')
      };
    };

    const getRuleTargetBadgeClass = (target) => {
      if (target === 'DIRECT') return 'bg-emerald-500/20 text-emerald-300';
      if (target === 'REJECT') return 'bg-red-500/20 text-red-300';
      return 'bg-indigo-500/20 text-indigo-300';
    };

    // API Calls
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        Object.assign(status, data);
      } catch (e) {
        console.error('Fetch status failed:', e);
      }
    };

    const fetchConfig = async () => {
      try {
        const res = await fetch(`/api/config?target=${currentTarget.value}`);
        const data = await res.json();
        if (data.success) {
          proxies.value = data.proxies || [];
          proxyGroups.value = data.proxy_groups || [];
          rules.value = data.rules || [];
          rawYaml.value = data.raw_yaml || '';
          status.config_path = data.path;
          refreshIcons();
        }
      } catch (e) {
        showToast('读取飞牛配置失败: ' + e.message, 'error');
      }
    };

    const fetchBackups = async () => {
      try {
        const res = await fetch(`/api/backups?target=${currentTarget.value}`);
        const data = await res.json();
        if (data.success) {
          backups.value = data.backups || [];
        }
      } catch (e) {
        console.error('Fetch backups error:', e);
      }
    };

    const switchTarget = (target) => {
      currentTarget.value = target;
      fetchConfig();
      fetchBackups();
    };

    // Test Latency
    const testSingleDelay = async (name) => {
      delays[name] = undefined;
      try {
        const res = await fetch(`/api/proxies/delay?name=${encodeURIComponent(name)}`);
        const data = await res.json();
        if (data.success) {
          delays[name] = data.delay;
        } else {
          delays[name] = 0; // timeout/error
        }
      } catch (e) {
        delays[name] = 0;
      }
    };

    const testAllDelays = async () => {
      isTestingAllDelays.value = true;
      const list = filteredProxies.value;
      
      // Concurrently test 5 at a time
      const batchSize = 5;
      for (let i = 0; i < list.length; i += batchSize) {
        const batch = list.slice(i, i + batchSize);
        await Promise.all(batch.map(node => testSingleDelay(node.name)));
      }
      isTestingAllDelays.value = false;
      showToast('全部节点延迟测试完毕！');
    };

    // Copy Share Link
    const copyShareLink = async (node) => {
      const link = node._share_link;
      if (!link) {
        showToast('该节点暂无可用分享链接', 'error');
        return;
      }
      try {
        await navigator.clipboard.writeText(link);
        showToast(`已复制【${node.name}】分享链接到剪贴板！`);
      } catch (e) {
        showToast('复制失败: ' + e.message, 'error');
      }
    };

    // Node Form Operations
    const openAddNodeModal = () => {
      isEditingNode.value = false;
      editingNodeIndex.value = -1;
      quickLinkInput.value = '';
      Object.assign(nodeForm, {
        name: '',
        type: 'vless',
        server: '',
        port: 443,
        uuid: '',
        password: '',
        cipher: 'aes-256-gcm',
        auth: '',
        network: 'tcp',
        tls: true,
        flow: 'xtls-rprx-vision',
        servername: 'www.bing.com',
        is_reality: true,
        reality_pbk: '',
        reality_sid: '',
        client_fp: 'chrome',
        udp: true
      });
      showNodeModal.value = true;
      refreshIcons();
    };

    const editNode = (node) => {
      isEditingNode.value = true;
      const idx = proxies.value.findIndex(p => p.name === node.name);
      editingNodeIndex.value = idx;
      quickLinkInput.value = '';

      const reality = node['reality-opts'] || {};
      Object.assign(nodeForm, {
        name: node.name || '',
        type: node.type || 'vless',
        server: node.server || '',
        port: node.port || 443,
        uuid: node.uuid || '',
        password: node.password || '',
        cipher: node.cipher || 'aes-256-gcm',
        auth: node.auth || '',
        network: node.network || 'tcp',
        tls: Boolean(node.tls || node['reality-opts']),
        flow: node.flow || '',
        servername: node.servername || node.sni || '',
        is_reality: Boolean(node['reality-opts']),
        reality_pbk: reality['public-key'] || '',
        reality_sid: reality['short-id'] || '',
        client_fp: node['client-fingerprint'] || 'chrome',
        udp: node.udp !== false
      });
      showNodeModal.value = true;
      refreshIcons();
    };

    const duplicateNode = (node) => {
      const copy = JSON.parse(JSON.stringify(node));
      copy.name = `${copy.name}-副本`;
      proxies.value.push(copy);
      showToast(`已克隆节点: ${copy.name}`);
      refreshIcons();
    };

    const deleteNode = (name) => {
      if (confirm(`确定要删除代理节点【${name}】吗？`)) {
        proxies.value = proxies.value.filter(p => p.name !== name);
        // Remove from groups
        proxyGroups.value.forEach(g => {
          if (Array.isArray(g.proxies)) {
            g.proxies = g.proxies.filter(p => p !== name);
          }
        });
        showToast(`节点【${name}】已删除`);
        refreshIcons();
      }
    };

    const parseQuickLink = () => {
      const link = quickLinkInput.value.trim();
      if (!link) return;
      try {
        if (link.startsWith('vless://')) {
          const u = new URL(link);
          const params = new URLSearchParams(u.search);
          nodeForm.type = 'vless';
          nodeForm.server = u.hostname;
          nodeForm.port = parseInt(u.port || 443);
          nodeForm.uuid = u.username;
          nodeForm.name = decodeURIComponent(u.hash.replace('#', '')) || `${nodeForm.server}:${nodeForm.port}`;
          nodeForm.network = params.get('type') || 'tcp';
          nodeForm.flow = params.get('flow') || '';
          nodeForm.servername = params.get('sni') || params.get('peer') || 'www.bing.com';
          nodeForm.tls = params.get('security') === 'tls' || params.get('security') === 'reality';
          nodeForm.is_reality = params.get('security') === 'reality';
          nodeForm.reality_pbk = params.get('pbk') || '';
          nodeForm.reality_sid = params.get('sid') || '';
          nodeForm.client_fp = params.get('fp') || 'chrome';
          showToast('VLESS 链接解析成功！');
        } else if (link.startsWith('trojan://')) {
          const u = new URL(link);
          const params = new URLSearchParams(u.search);
          nodeForm.type = 'trojan';
          nodeForm.server = u.hostname;
          nodeForm.port = parseInt(u.port || 443);
          nodeForm.password = u.username;
          nodeForm.name = decodeURIComponent(u.hash.replace('#', '')) || `${nodeForm.server}:${nodeForm.port}`;
          nodeForm.servername = params.get('sni') || '';
          showToast('Trojan 链接解析成功！');
        } else if (link.startsWith('hysteria2://') || link.startsWith('hy2://')) {
          const u = new URL(link.replace('hy2://', 'hysteria2://'));
          const params = new URLSearchParams(u.search);
          nodeForm.type = 'hysteria2';
          nodeForm.server = u.hostname;
          nodeForm.port = parseInt(u.port || 443);
          nodeForm.auth = u.username;
          nodeForm.name = decodeURIComponent(u.hash.replace('#', '')) || `${nodeForm.server}:${nodeForm.port}`;
          nodeForm.servername = params.get('sni') || '';
          showToast('Hysteria2 链接解析成功！');
        } else {
          showToast('该格式请使用“批量导入”或直接手动填写', 'info');
        }
      } catch (e) {
        showToast('解析失败: ' + e.message, 'error');
      }
    };

    const submitNodeForm = () => {
      if (!nodeForm.name || !nodeForm.server || !nodeForm.port) {
        showToast('请填写完整的节点名称、服务器和端口！', 'error');
        return;
      }

      const proxyObj = {
        name: nodeForm.name.trim(),
        type: nodeForm.type,
        server: nodeForm.server.trim(),
        port: parseInt(nodeForm.port),
        udp: nodeForm.udp
      };

      if (['vless', 'vmess'].includes(nodeForm.type)) {
        proxyObj.uuid = nodeForm.uuid.trim();
        proxyObj.network = nodeForm.network;
      }

      if (nodeForm.type === 'vless') {
        if (nodeForm.flow) proxyObj.flow = nodeForm.flow.trim();
        if (nodeForm.is_reality) {
          proxyObj.tls = true;
          proxyObj['reality-opts'] = {
            'public-key': nodeForm.reality_pbk.trim(),
            'short-id': nodeForm.reality_sid.trim()
          };
          if (nodeForm.servername) proxyObj.servername = nodeForm.servername.trim();
          if (nodeForm.client_fp) proxyObj['client-fingerprint'] = nodeForm.client_fp.trim();
        } else if (nodeForm.tls) {
          proxyObj.tls = true;
          if (nodeForm.servername) proxyObj.servername = nodeForm.servername.trim();
        }
      } else if (nodeForm.type === 'trojan') {
        proxyObj.password = nodeForm.password.trim();
        if (nodeForm.servername) proxyObj.sni = nodeForm.servername.trim();
      } else if (nodeForm.type === 'ss') {
        proxyObj.cipher = nodeForm.cipher.trim();
        proxyObj.password = nodeForm.password.trim();
      } else if (nodeForm.type === 'hysteria2') {
        proxyObj.auth = nodeForm.auth.trim();
        if (nodeForm.servername) proxyObj.sni = nodeForm.servername.trim();
      }

      if (isEditingNode.value && editingNodeIndex.value >= 0) {
        const oldName = proxies.value[editingNodeIndex.value].name;
        proxies.value[editingNodeIndex.value] = proxyObj;
        // Update name in groups if changed
        if (oldName !== proxyObj.name) {
          proxyGroups.value.forEach(g => {
            if (Array.isArray(g.proxies)) {
              const idx = g.proxies.indexOf(oldName);
              if (idx !== -1) g.proxies[idx] = proxyObj.name;
            }
          });
        }
        showToast(`节点【${proxyObj.name}】更新成功！`);
      } else {
        proxies.value.push(proxyObj);
        // Auto add to PROXY group
        const proxyGroup = proxyGroups.value.find(g => g.name === 'PROXY');
        if (proxyGroup && Array.isArray(proxyGroup.proxies)) {
          if (!proxyGroup.proxies.includes(proxyObj.name)) {
            proxyGroup.proxies.unshift(proxyObj.name);
          }
        }
        showToast(`节点【${proxyObj.name}】添加成功！`);
      }

      showNodeModal.value = false;
      refreshIcons();
    };

    // Batch Import
    const openBatchModal = () => {
      batchInputText.value = '';
      batchAddToProxyGroup.value = true;
      showBatchModal.value = true;
      refreshIcons();
    };

    const submitBatchImport = async () => {
      if (!batchInputText.value.trim()) {
        showToast('请输入要导入的内容！', 'error');
        return;
      }
      try {
        const res = await fetch('/api/proxies/batch-import', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: batchInputText.value,
            add_to_groups: batchAddToProxyGroup.value ? ['PROXY'] : [],
            auto_reload: true,
            target: currentTarget.value
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message);
          showBatchModal.value = false;
          fetchConfig();
        } else {
          showToast(data.detail || '导入失败', 'error');
        }
      } catch (e) {
        showToast('导入失败: ' + e.message, 'error');
      }
    };

    // Subscription Import
    const openSubModal = () => {
      subUrlInput.value = '';
      fetchedSubProxies.value = [];
      selectedSubIndices.value = [];
      showSubModal.value = true;
      refreshIcons();
    };

    const fetchSubscriptionNodes = async () => {
      if (!subUrlInput.value.trim()) {
        showToast('请输入订阅链接！', 'error');
        return;
      }
      isFetchingSub.value = true;
      try {
        const res = await fetch('/api/subscription/fetch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: subUrlInput.value.trim() })
        });
        const data = await res.json();
        if (data.success) {
          fetchedSubProxies.value = data.proxies || [];
          selectedSubIndices.value = (data.proxies || []).map((_, i) => i);
          showToast(`成功获取 ${fetchedSubProxies.value.length} 个节点！`);
        } else {
          showToast(data.detail || '拉取订阅失败', 'error');
        }
      } catch (e) {
        showToast('拉取订阅失败: ' + e.message, 'error');
      } finally {
        isFetchingSub.value = false;
      }
    };

    const toggleSelectAllSub = () => {
      if (selectedSubIndices.value.length === fetchedSubProxies.value.length) {
        selectedSubIndices.value = [];
      } else {
        selectedSubIndices.value = fetchedSubProxies.value.map((_, i) => i);
      }
    };

    const importSelectedSubProxies = () => {
      const selected = selectedSubIndices.value.map(i => fetchedSubProxies.value[i]);
      let addedCount = 0;
      selected.forEach(node => {
        let name = node.name;
        let counter = 1;
        while (proxies.value.some(p => p.name === name)) {
          name = `${node.name}-${counter++}`;
        }
        node.name = name;
        proxies.value.push(node);
        addedCount++;
      });
      showToast(`成功导入 ${addedCount} 个订阅节点，请点击“保存并生效”！`);
      showSubModal.value = false;
      refreshIcons();
    };

    // Strategy Groups
    const isProxyInGroup = (group, nodeName) => {
      return Array.isArray(group.proxies) && group.proxies.includes(nodeName);
    };

    const toggleProxyInGroup = (group, nodeName) => {
      if (!Array.isArray(group.proxies)) group.proxies = [];
      const idx = group.proxies.indexOf(nodeName);
      if (idx !== -1) {
        group.proxies.splice(idx, 1);
      } else {
        group.proxies.push(nodeName);
      }
    };

    const openAddGroupModal = () => {
      const name = prompt('请输入新策略组名称 (例如: NETFLIX, EMBY, STEAM):');
      if (name) {
        proxyGroups.value.push({
          name: name.trim(),
          type: 'select',
          proxies: ['PROXY', 'DIRECT']
        });
        showToast(`已创建策略组: ${name}`);
      }
    };

    // Rules
    const openAddRuleModal = () => {
      const type = prompt('请输入规则类型 (DOMAIN-SUFFIX, DOMAIN, IP-CIDR, GEOIP):', 'DOMAIN-SUFFIX');
      if (!type) return;
      const payload = prompt('请输入匹配域名或IP (例如: tmdb.org, google.com, 192.168.1.0/24):', '');
      if (!payload) return;
      const target = prompt('请输入目标策略组或动作 (PROXY, DIRECT, TMDB, REJECT):', 'PROXY');
      if (!target) return;

      const ruleStr = `${type},${payload},${target}`;
      rules.value.unshift(ruleStr);
      showToast('规则添加成功！');
    };

    const deleteRule = (idx) => {
      rules.value.splice(idx, 1);
      showToast('规则已删除');
    };

    const moveRule = (idx, dir) => {
      const targetIdx = idx + dir;
      if (targetIdx < 0 || targetIdx >= rules.value.length) return;
      const temp = rules.value[idx];
      rules.value[idx] = rules.value[targetIdx];
      rules.value[targetIdx] = temp;
    };

    // Save All & Apply
    const saveAndApply = async () => {
      isSaving.value = true;
      try {
        const res = await fetch('/api/proxies/save-all', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            proxies: proxies.value,
            proxy_groups: proxyGroups.value,
            rules: rules.value,
            auto_reload: true,
            target: currentTarget.value
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message + (data.reload ? ` (${data.reload.message})` : ''));
          fetchConfig();
          fetchBackups();
        } else {
          showToast(data.detail || '保存失败', 'error');
        }
      } catch (e) {
        showToast('保存失败: ' + e.message, 'error');
      } finally {
        isSaving.value = false;
      }
    };

    const saveRawYaml = async () => {
      try {
        const res = await fetch('/api/config/save-raw', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            raw_yaml: rawYaml.value,
            target: currentTarget.value,
            auto_reload: true
          })
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message + (data.reload ? ` (${data.reload.message})` : ''));
          fetchConfig();
          fetchBackups();
        } else {
          showToast(data.detail || '保存失败', 'error');
        }
      } catch (e) {
        showToast('保存失败: ' + e.message, 'error');
      }
    };

    const restoreBackup = async (path) => {
      if (confirm(`确定要将配置回滚到备份文件 ${path} 吗？`)) {
        try {
          const res = await fetch('/api/backups/restore', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              backup_path: path,
              target: currentTarget.value
            })
          });
          const data = await res.json();
          if (data.success) {
            showToast('备份恢复成功！');
            fetchConfig();
          } else {
            showToast(data.detail || '恢复备份失败', 'error');
          }
        } catch (e) {
          showToast('恢复备份失败: ' + e.message, 'error');
        }
      }
    };

    const restartMihomo = async () => {
      if (confirm('确定要重启飞牛上的 Mihomo 容器吗？')) {
        try {
          const res = await fetch('/api/mihomo/restart', { method: 'POST' });
          const data = await res.json();
          if (data.success) {
            showToast(data.message);
            fetchStatus();
          }
        } catch (e) {
          showToast('重启容器失败: ' + e.message, 'error');
        }
      }
    };

    // Settings
    const openSettingsModal = async () => {
      try {
        const res = await fetch('/api/settings');
        const data = await res.json();
        Object.assign(settingsForm, data);
        showSettingsModal.value = true;
        refreshIcons();
      } catch (e) {
        console.error(e);
      }
    };

    const saveSettings = async () => {
      try {
        const res = await fetch('/api/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(settingsForm)
        });
        const data = await res.json();
        if (data.success) {
          showToast('设置保存成功！');
          showSettingsModal.value = false;
          fetchStatus();
          fetchConfig();
        }
      } catch (e) {
        showToast('设置保存失败: ' + e.message, 'error');
      }
    };

    // Lifecycle
    onMounted(() => {
      fetchStatus();
      fetchConfig();
      fetchBackups();
      refreshIcons();
      // Polling status
      setInterval(fetchStatus, 15000);
    });

    watch(activeTab, () => {
      refreshIcons();
    });

    return {
      activeTab,
      currentTarget,
      isSaving,
      isTestingAllDelays,
      isFetchingSub,
      status,
      proxies,
      proxyGroups,
      rules,
      rawYaml,
      delays,
      backups,
      searchQuery,
      selectedProtocol,
      filteredProxies,
      availableProxyNames,
      toast,
      showToast,
      // Modals
      showNodeModal,
      isEditingNode,
      nodeForm,
      quickLinkInput,
      openAddNodeModal,
      editNode,
      duplicateNode,
      deleteNode,
      parseQuickLink,
      submitNodeForm,
      // Batch
      showBatchModal,
      batchInputText,
      batchAddToProxyGroup,
      openBatchModal,
      submitBatchImport,
      // Sub
      showSubModal,
      subUrlInput,
      fetchedSubProxies,
      selectedSubIndices,
      openSubModal,
      fetchSubscriptionNodes,
      toggleSelectAllSub,
      importSelectedSubProxies,
      // Groups & Rules
      isProxyInGroup,
      toggleProxyInGroup,
      openAddGroupModal,
      parseRule,
      getRuleTargetBadgeClass,
      openAddRuleModal,
      deleteRule,
      moveRule,
      // Actions
      switchTarget,
      testSingleDelay,
      testAllDelays,
      copyShareLink,
      saveAndApply,
      saveRawYaml,
      fetchBackups,
      restoreBackup,
      restartMihomo,
      openSettingsModal,
      saveSettings,
      settingsForm,
      getProtocolBadgeClass,
      getDelayBadgeClass,
      getDelayDotClass
    };
  }
});

app.mount('#app');
