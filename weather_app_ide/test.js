// Verification Test Harness for Quality Assurance, Boundary Testing & Verification
function runVerification() {
  const errors = [];
  const assert = (condition, msg) => { if(!condition) errors.push(msg); };

  // Test 1: Data Initialization
  assert(typeof appInstance === 'object', 'Instance initialized properly');

  // Test 2: State Immutability
  const before = appInstance.state.records.length;
  appInstance.dispatch('CREATE_ITEM', { title: 'Test Record' });
  assert(appInstance.state.records.length === before + 1, 'State item count incremented');

  // Test 3: ID Uniqueness
  const ids = appInstance.state.records.map(i => i.id);
  const uniqueIds = new Set(ids);
  assert(ids.length === uniqueIds.size, 'All record IDs are unique');

  if(errors.length === 0) {
    console.log('✅ ALL VERIFICATIONS PASSED (3/3).');
  } else {
    console.error('❌ Tests failed:', errors);
  }
}
runVerification();